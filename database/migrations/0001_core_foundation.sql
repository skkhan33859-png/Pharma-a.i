-- =====================================================
-- PHARMA ERP
-- PHASE 1: CORE FOUNDATION
-- Database: Supabase PostgreSQL
-- =====================================================

-- 1. ROLE TYPES
CREATE TYPE public.organization_role AS ENUM (
    'owner',
    'admin',
    'manager',
    'staff'
);

CREATE TYPE public.branch_role AS ENUM (
    'manager',
    'purchase',
    'sales',
    'billing',
    'inventory',
    'accountant',
    'viewer'
);

-- 2. USER PROFILES
CREATE TABLE public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT,
    phone TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. ORGANIZATIONS
CREATE TABLE public.organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE,
    created_by UUID NOT NULL REFERENCES auth.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. BRANCHES
CREATE TABLE public.branches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL
        REFERENCES public.organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    code TEXT NOT NULL,
    address TEXT,
    phone TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (organization_id, code),
    UNIQUE (id, organization_id)
);

-- 5. ORGANIZATION MEMBERSHIPS
CREATE TABLE public.organization_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL
        REFERENCES public.organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL
        REFERENCES auth.users(id) ON DELETE CASCADE,
    role public.organization_role NOT NULL DEFAULT 'staff',
    invited_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (organization_id, user_id)
);

-- 6. BRANCH MEMBERSHIPS
CREATE TABLE public.branch_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    branch_id UUID NOT NULL,
    user_id UUID NOT NULL
        REFERENCES auth.users(id) ON DELETE CASCADE,
    role public.branch_role NOT NULL DEFAULT 'viewer',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    FOREIGN KEY (branch_id, organization_id)
        REFERENCES public.branches(id, organization_id)
        ON DELETE CASCADE,

    UNIQUE (branch_id, user_id)
);

-- 7. INDEXES
CREATE INDEX idx_branches_organization
ON public.branches(organization_id);

CREATE INDEX idx_org_memberships_user
ON public.organization_memberships(user_id);

CREATE INDEX idx_org_memberships_org
ON public.organization_memberships(organization_id);

CREATE INDEX idx_branch_memberships_user
ON public.branch_memberships(user_id);

CREATE INDEX idx_branch_memberships_branch
ON public.branch_memberships(branch_id);

-- 8. SECURITY HELPER FUNCTIONS

CREATE OR REPLACE FUNCTION public.has_org_role(
    p_org_id UUID,
    p_roles public.organization_role[]
)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.organization_memberships m
        WHERE m.organization_id = p_org_id
          AND m.user_id = auth.uid()
          AND m.role = ANY(p_roles)
    );
$$;

CREATE OR REPLACE FUNCTION public.is_org_member(
    p_org_id UUID
)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.organization_memberships m
        WHERE m.organization_id = p_org_id
          AND m.user_id = auth.uid()
    );
$$;

CREATE OR REPLACE FUNCTION public.is_branch_member(
    p_branch_id UUID
)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.branch_memberships bm
        WHERE bm.branch_id = p_branch_id
          AND bm.user_id = auth.uid()
    );
$$;

-- 9. ENABLE ROW LEVEL SECURITY

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.branches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.organization_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.branch_memberships ENABLE ROW LEVEL SECURITY;

-- 10. PROFILE POLICIES

CREATE POLICY profiles_select_own
ON public.profiles
FOR SELECT
TO authenticated
USING (id = auth.uid());

CREATE POLICY profiles_insert_own
ON public.profiles
FOR INSERT
TO authenticated
WITH CHECK (id = auth.uid());

CREATE POLICY profiles_update_own
ON public.profiles
FOR UPDATE
TO authenticated
USING (id = auth.uid())
WITH CHECK (id = auth.uid());

-- 11. ORGANIZATION POLICIES

CREATE POLICY organizations_select_member
ON public.organizations
FOR SELECT
TO authenticated
USING (public.is_org_member(id));

-- 12. BRANCH POLICIES

CREATE POLICY branches_select_member
ON public.branches
FOR SELECT
TO authenticated
USING (public.is_org_member(organization_id));

-- 13. ORGANIZATION MEMBERSHIP POLICIES

CREATE POLICY org_memberships_select
ON public.organization_memberships
FOR SELECT
TO authenticated
USING (
    user_id = auth.uid()
    OR public.has_org_role(
        organization_id,
        ARRAY['owner', 'admin']::public.organization_role[]
    )
);

-- 14. BRANCH MEMBERSHIP POLICIES

CREATE POLICY branch_memberships_select
ON public.branch_memberships
FOR SELECT
TO authenticated
USING (
    user_id = auth.uid()
    OR public.has_org_role(
        organization_id,
        ARRAY['owner', 'admin']::public.organization_role[]
    )
);

-- 15. FUNCTION PERMISSIONS

REVOKE ALL ON FUNCTION public.has_org_role(
    UUID, public.organization_role[]
) FROM PUBLIC;

REVOKE ALL ON FUNCTION public.is_org_member(UUID) FROM PUBLIC;

REVOKE ALL ON FUNCTION public.is_branch_member(UUID) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.has_org_role(
    UUID, public.organization_role[]
) TO authenticated;

GRANT EXECUTE ON FUNCTION public.is_org_member(UUID)
TO authenticated;

GRANT EXECUTE ON FUNCTION public.is_branch_member(UUID)
TO authenticated;

-- =====================================================
-- PHASE 1 CORE FOUNDATION COMPLETE
-- =====================================================
