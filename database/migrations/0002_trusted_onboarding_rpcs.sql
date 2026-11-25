-- =====================================================
-- PHARMA ERP
-- PHASE 1: TRUSTED ONBOARDING FUNCTIONS
-- =====================================================

-- 1. CREATE ORGANIZATION
CREATE OR REPLACE FUNCTION public.create_organization(
    p_name TEXT,
    p_slug TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
SET row_security = off
AS $$
DECLARE
    v_user_id UUID;
    v_org_id UUID;
BEGIN
    v_user_id := auth.uid();

    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'Authentication required';
    END IF;

    IF p_name IS NULL OR LENGTH(TRIM(p_name)) = 0 THEN
        RAISE EXCEPTION 'Organization name is required';
    END IF;

    INSERT INTO public.organizations (
        name,
        slug,
        created_by
    )
    VALUES (
        TRIM(p_name),
        NULLIF(TRIM(p_slug), ''),
        v_user_id
    )
    RETURNING id INTO v_org_id;

    INSERT INTO public.organization_memberships (
        organization_id,
        user_id,
        role
    )
    VALUES (
        v_org_id,
        v_user_id,
        'owner'
    );

    RETURN v_org_id;
END;
$$;


-- 2. CREATE BRANCH
CREATE OR REPLACE FUNCTION public.create_branch(
    p_org_id UUID,
    p_name TEXT,
    p_code TEXT,
    p_address TEXT DEFAULT NULL,
    p_phone TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
SET row_security = off
AS $$
DECLARE
    v_branch_id UUID;
BEGIN
    IF auth.uid() IS NULL THEN
        RAISE EXCEPTION 'Authentication required';
    END IF;

    IF NOT public.has_org_role(
        p_org_id,
        ARRAY['owner', 'admin']::public.organization_role[]
    ) THEN
        RAISE EXCEPTION 'Permission denied';
    END IF;

    IF p_name IS NULL OR LENGTH(TRIM(p_name)) = 0 THEN
        RAISE EXCEPTION 'Branch name is required';
    END IF;

    IF p_code IS NULL OR LENGTH(TRIM(p_code)) = 0 THEN
        RAISE EXCEPTION 'Branch code is required';
    END IF;

    INSERT INTO public.branches (
        organization_id,
        name,
        code,
        address,
        phone
    )
    VALUES (
        p_org_id,
        TRIM(p_name),
        UPPER(TRIM(p_code)),
        NULLIF(TRIM(p_address), ''),
        NULLIF(TRIM(p_phone), '')
    )
    RETURNING id INTO v_branch_id;

    RETURN v_branch_id;
END;
$$;


-- 3. ADD ORGANIZATION MEMBER
CREATE OR REPLACE FUNCTION public.add_organization_member(
    p_org_id UUID,
    p_user_id UUID,
    p_role public.organization_role
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
SET row_security = off
AS $$
DECLARE
    v_membership_id UUID;
    v_actor_role public.organization_role;
BEGIN
    IF auth.uid() IS NULL THEN
        RAISE EXCEPTION 'Authentication required';
    END IF;

    SELECT role
    INTO v_actor_role
    FROM public.organization_memberships
    WHERE organization_id = p_org_id
      AND user_id = auth.uid();

    IF v_actor_role IS NULL
       OR v_actor_role NOT IN ('owner', 'admin') THEN
        RAISE EXCEPTION 'Permission denied';
    END IF;

    IF p_user_id IS NULL THEN
        RAISE EXCEPTION 'User ID is required';
    END IF;

    IF p_role IS NULL OR p_role = 'owner' THEN
        RAISE EXCEPTION 'Invalid member role';
    END IF;

    IF v_actor_role = 'admin' AND p_role = 'admin' THEN
        RAISE EXCEPTION 'Only owner can assign admin role';
    END IF;

    INSERT INTO public.organization_memberships (
        organization_id,
        user_id,
        role,
        invited_by
    )
    VALUES (
        p_org_id,
        p_user_id,
        p_role,
        auth.uid()
    )
    ON CONFLICT (organization_id, user_id)
    DO UPDATE SET
        role = EXCLUDED.role,
        invited_by = EXCLUDED.invited_by
    WHERE public.organization_memberships.role <> 'owner'
    RETURNING id INTO v_membership_id;

    IF v_membership_id IS NULL THEN
        RAISE EXCEPTION 'Cannot modify owner membership';
    END IF;

    RETURN v_membership_id;
END;
$$;


-- 4. ASSIGN BRANCH MEMBER
CREATE OR REPLACE FUNCTION public.assign_branch_member(
    p_org_id UUID,
    p_branch_id UUID,
    p_user_id UUID,
    p_role public.branch_role
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
SET row_security = off
AS $$
DECLARE
    v_membership_id UUID;
BEGIN
    IF auth.uid() IS NULL THEN
        RAISE EXCEPTION 'Authentication required';
    END IF;

    IF NOT public.has_org_role(
        p_org_id,
        ARRAY['owner', 'admin']::public.organization_role[]
    ) THEN
        RAISE EXCEPTION 'Permission denied';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM public.branches
        WHERE id = p_branch_id
          AND organization_id = p_org_id
    ) THEN
        RAISE EXCEPTION 'Branch does not belong to organization';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM public.organization_memberships
        WHERE organization_id = p_org_id
          AND user_id = p_user_id
    ) THEN
        RAISE EXCEPTION 'User is not an organization member';
    END IF;

    IF p_role IS NULL THEN
        RAISE EXCEPTION 'Branch role is required';
    END IF;

    INSERT INTO public.branch_memberships (
        organization_id,
        branch_id,
        user_id,
        role
    )
    VALUES (
        p_org_id,
        p_branch_id,
        p_user_id,
        p_role
    )
    ON CONFLICT (branch_id, user_id)
    DO UPDATE SET
        role = EXCLUDED.role
    RETURNING id INTO v_membership_id;

    RETURN v_membership_id;
END;
$$;


-- 5. FUNCTION PERMISSIONS

REVOKE ALL ON FUNCTION
public.create_organization(TEXT, TEXT)
FROM PUBLIC;

REVOKE ALL ON FUNCTION
public.create_branch(UUID, TEXT, TEXT, TEXT, TEXT)
FROM PUBLIC;

REVOKE ALL ON FUNCTION
public.add_organization_member(
    UUID, UUID, public.organization_role
)
FROM PUBLIC;

REVOKE ALL ON FUNCTION
public.assign_branch_member(
    UUID, UUID, UUID, public.branch_role
)
FROM PUBLIC;


GRANT EXECUTE ON FUNCTION
public.create_organization(TEXT, TEXT)
TO authenticated;

GRANT EXECUTE ON FUNCTION
public.create_branch(UUID, TEXT, TEXT, TEXT, TEXT)
TO authenticated;

GRANT EXECUTE ON FUNCTION
public.add_organization_member(
    UUID, UUID, public.organization_role
)
TO authenticated;

GRANT EXECUTE ON FUNCTION
public.assign_branch_member(
    UUID, UUID, UUID, public.branch_role
)
TO authenticated;


-- =====================================================
-- PHASE 1 ONBOARDING FUNCTIONS COMPLETE
-- =====================================================
