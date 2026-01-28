"use client";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

type Props = {
  data: { source: string; count: number }[];
};

export default function CompanyComparisonChart({ data }: Props) {
  console.log("✅ CompanyComparisonChart mounted", { data });

  if (!data || data.length === 0) {
    return (
      <div className="text-sm text-muted-foreground">
        No analytics data yet (try running RAG search / dashboard once).
      </div>
    );
  }

  return (
    <div style={{ width: "100%", height: 280 }}>
      <ResponsiveContainer>
        <BarChart data={data}>
          <XAxis dataKey="source" />
          <YAxis />
          <Tooltip />
          <Bar dataKey="count" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
