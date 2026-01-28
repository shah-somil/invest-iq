"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

const data = [
  { date: "2024-01", price: 120 },
  { date: "2024-02", price: 128 },
  { date: "2024-03", price: 123 },
  { date: "2024-04", price: 135 },
  { date: "2024-05", price: 142 },
  { date: "2024-06", price: 150 },
];

export default function PriceTrendChart() {
  return (
    <div style={{ width: "100%", height: 280 }}>
      <ResponsiveContainer>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="price" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
