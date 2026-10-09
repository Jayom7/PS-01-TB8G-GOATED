/** OAuth/recovery can only return to these same-origin product routes. */
export function authDestination(value: string | null): string {
  return value === "/reset-password" ? "/reset-password" : "/dashboard";
}
