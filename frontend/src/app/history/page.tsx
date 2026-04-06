"use client";

import { useState } from "react";
import { useApi } from "@/hooks/use-api";
import { getDevices, getHistory } from "@/lib/api";
import type { DeviceResponse, HistoryResponse } from "@/lib/types";
import { HistoryFilters } from "@/components/history/history-filters";
import { HistoryChart } from "@/components/history/history-chart";
import { HistoryTable } from "@/components/history/history-table";

function defaultStartDate(): string {
  const d = new Date();
  d.setDate(d.getDate() - 7);
  return d.toISOString().slice(0, 10);
}

function defaultEndDate(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function HistoryPage() {
  const [startDate, setStartDate] = useState(defaultStartDate);
  const [endDate, setEndDate] = useState(defaultEndDate);
  const [groupBy, setGroupBy] = useState("day");
  const [deviceId, setDeviceId] = useState("all");

  const devices = useApi<DeviceResponse[]>(() => getDevices());

  const history = useApi<HistoryResponse>(
    () =>
      getHistory({
        start_date: startDate,
        end_date: endDate,
        group_by: groupBy,
        device_id: deviceId === "all" ? undefined : deviceId,
      }),
    { deps: [startDate, endDate, groupBy, deviceId] }
  );

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4">
      <h2 className="text-2xl font-semibold tracking-tight">
        Vista Historica
      </h2>

      <HistoryFilters
        startDate={startDate}
        endDate={endDate}
        groupBy={groupBy}
        deviceId={deviceId}
        devices={devices.data ?? []}
        onStartDateChange={setStartDate}
        onEndDateChange={setEndDate}
        onGroupByChange={setGroupBy}
        onDeviceIdChange={setDeviceId}
      />

      {history.isLoading && !history.data ? (
        <p className="text-muted-foreground text-center py-8">Cargando...</p>
      ) : history.error ? (
        <p className="text-destructive text-center py-8">
          Error: {history.error}
        </p>
      ) : (
        <>
          <HistoryChart
            data={history.data?.data ?? []}
            groupBy={groupBy}
          />
          <HistoryTable
            data={history.data?.data ?? []}
            groupBy={groupBy}
          />
        </>
      )}
    </div>
  );
}
