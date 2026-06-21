/** Connection / provider domain types — the bank / telematics / meter sources. */

import type { FootprintSummary } from "./footprint";

export interface DataConnection {
  id: "bank" | "telematics" | "meter";
  label: string;
  status: "disconnected" | "connecting" | "connected" | "needs-attention";
  lastSync?: string;
}

/** Result of connecting a (sandbox) data source — docs/API-DESIGN.md §4. */
export interface ConnectResult {
  connection: DataConnection;
  recordsImported: number;
  summary: FootprintSummary;
}

/** Sources the user can connect from the UI. */
export type ConnectProvider = "bank" | "meter";
