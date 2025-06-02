/**
 * Utility functions for case conversion
 */

/**
 * Converts object keys from PascalCase to camelCase
 * @param obj The object to convert
 * @returns A new object with camelCase keys
 */
export function toCamelCase(obj: Record<string, any>): Record<string, any> {
  const result: Record<string, any> = {};
  
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      // Convert first character to lowercase for the new key
      const camelKey = key.charAt(0).toLowerCase() + key.slice(1);
      result[camelKey] = obj[key];
    }
  }
  
  return result;
}

/**
 * Recursively converts all object keys from PascalCase to camelCase
 * including nested objects and arrays
 * @param obj The object to convert
 * @returns A new object with all keys in camelCase
 */
export function toCamelCaseDeep(obj: any): any {
  if (obj === null || typeof obj !== 'object') {
    return obj;
  }

  if (Array.isArray(obj)) {
    return obj.map(item => toCamelCaseDeep(item));
  }

  const result: Record<string, any> = {};
  
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      const camelKey = key.charAt(0).toLowerCase() + key.slice(1);
      result[camelKey] = toCamelCaseDeep(obj[key]);
    }
  }
  
  return result;
}
