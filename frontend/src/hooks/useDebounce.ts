/**
 * useDebounce — 防抖 hook
 * 在指定延迟后才更新返回值，适用于搜索输入等场景
 */
import { useState, useEffect } from 'react';

/**
 * 防抖 hook
 * @param value - 需要防抖的值
 * @param delay - 延迟毫秒数
 * @returns 防抖后的值
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}

export default useDebounce;
