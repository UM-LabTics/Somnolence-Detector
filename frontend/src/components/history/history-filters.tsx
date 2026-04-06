"use client";

import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { DeviceResponse } from "@/lib/types";

interface HistoryFiltersProps {
  startDate: string;
  endDate: string;
  groupBy: string;
  deviceId: string;
  devices: DeviceResponse[];
  onStartDateChange: (v: string) => void;
  onEndDateChange: (v: string) => void;
  onGroupByChange: (v: string) => void;
  onDeviceIdChange: (v: string) => void;
}

export function HistoryFilters({
  startDate,
  endDate,
  groupBy,
  deviceId,
  devices,
  onStartDateChange,
  onEndDateChange,
  onGroupByChange,
  onDeviceIdChange,
}: HistoryFiltersProps) {
  return (
    <div className="flex flex-wrap items-end gap-4">
      <div className="space-y-1">
        <label className="text-sm font-medium text-muted-foreground">Desde</label>
        <Input
          type="date"
          value={startDate}
          onChange={(e) => onStartDateChange(e.target.value)}
          className="w-40"
        />
      </div>
      <div className="space-y-1">
        <label className="text-sm font-medium text-muted-foreground">Hasta</label>
        <Input
          type="date"
          value={endDate}
          onChange={(e) => onEndDateChange(e.target.value)}
          className="w-40"
        />
      </div>
      <div className="space-y-1">
        <label className="text-sm font-medium text-muted-foreground">Agrupar por</label>
        <Select value={groupBy} onValueChange={onGroupByChange}>
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="hour">Hora</SelectItem>
            <SelectItem value="day">Dia</SelectItem>
            <SelectItem value="month">Mes</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-1">
        <label className="text-sm font-medium text-muted-foreground">Dispositivo</label>
        <Select value={deviceId} onValueChange={onDeviceIdChange}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos los dispositivos</SelectItem>
            {devices.map((d) => (
              <SelectItem key={d.id} value={d.id}>
                {d.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
