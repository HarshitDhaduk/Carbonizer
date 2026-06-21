/** Authenticated-user domain type. */

export interface AuthUser {
  id: string;
  email: string;
  region: string;
  targetTco2e: number | null;
}
