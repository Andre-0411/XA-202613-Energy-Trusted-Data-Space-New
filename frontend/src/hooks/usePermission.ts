/**
 * usePermission — 权限检查 hook
 * 从 authStore 获取当前用户角色与权限列表，提供便捷的权限判断方法
 */
import { useMemo } from 'react';
import { useAuthStore } from '@/stores/authStore';

/** 已定义的系统角色 */
type SystemRole = 'admin' | 'data_admin' | 'user' | 'auditor' | 'operator';

interface UsePermissionReturn {
  /** 检查是否拥有指定权限 */
  hasPermission: (perm: string) => boolean;
  /** 检查是否为指定角色 */
  hasRole: (role: string) => boolean;
  /** 是否为超级管理员 */
  isAdmin: boolean;
  /** 是否为审计员 */
  isAuditor: boolean;
  /** 是否为数据管理员 */
  isDataAdmin: boolean;
  /** 当前用户角色 */
  currentRole: string;
  /** 当前权限列表 */
  permissions: string[];
}

/**
 * 权限检查 hook
 * @returns 权限判断方法与角色标志
 */
export function usePermission(): UsePermissionReturn {
  const user = useAuthStore((state) => state.user);
  const permissions = useAuthStore((state) => state.permissions);

  const currentRole = user?.role ?? '';

  /** 是否为管理员 */
  const isAdmin = useMemo(
    () => currentRole === 'admin' satisfies SystemRole,
    [currentRole],
  );

  /** 是否为审计员 */
  const isAuditor = useMemo(
    () => currentRole === 'auditor' satisfies SystemRole,
    [currentRole],
  );

  /** 是否为数据管理员 */
  const isDataAdmin = useMemo(
    () => currentRole === 'data_admin' satisfies SystemRole,
    [currentRole],
  );

  /** 检查是否拥有指定权限（超级管理员默认拥有全部权限） */
  const hasPermission = useMemo(() => {
    return (perm: string): boolean => {
      if (isAdmin) return true;
      return permissions.includes(perm);
    };
  }, [isAdmin, permissions]);

  /** 检查是否为指定角色 */
  const hasRole = useMemo(() => {
    return (role: string): boolean => {
      return currentRole === role;
    };
  }, [currentRole]);

  return {
    hasPermission,
    hasRole,
    isAdmin,
    isAuditor,
    isDataAdmin,
    currentRole,
    permissions,
  };
}

export default usePermission;
