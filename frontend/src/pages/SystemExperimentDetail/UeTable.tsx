import { Table, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import type { UserEquipmentResult } from '../../types/system';
import { EMPTY, formatPercent, isNumber } from '../../utils/format';
import type { UeField } from '../../utils/system';
import { unavailableReason } from '../../utils/system';

interface Props {
  ues: UserEquipmentResult[];
  onSelect: (ueId: string) => void;
}

/** 数值缺失时显示 "—" 并在悬停提示中给出原因。 */
export function UeValue({ ue, field, digits, unit }: { ue: UserEquipmentResult; field: UeField; digits: number; unit?: string }) {
  const v = ue[field];
  if (!isNumber(v)) {
    return (
      <Tooltip title={unavailableReason(ue, field)}>
        <span className="value-missing" data-testid={`missing-${ue.ue_id}-${field}`}>{EMPTY}</span>
      </Tooltip>
    );
  }
  return <span>{unit ? `${v.toFixed(digits)} ${unit}` : v.toFixed(digits)}</span>;
}

export function UeTable({ ues, onSelect }: Props) {
  const columns: ColumnsType<UserEquipmentResult> = [
    { title: 'UE', dataIndex: 'ue_id', render: (id: string) => <code>{id}</code> },
    { title: '服务小区 Serving Cell', dataIndex: 'serving_cell_id' },
    {
      title: 'SINR（有效）Eff. SINR',
      key: 'sinr',
      align: 'right',
      render: (_, u) => <UeValue ue={u} field="sinr_eff_db_mean" digits={2} unit="dB" />,
    },
    { title: 'MCS（均值）Mean MCS', key: 'mcs', align: 'right', render: (_, u) => <UeValue ue={u} field="mcs_index_mean" digits={1} /> },
    {
      title: '分配资源 Allocated RE',
      key: 're',
      align: 'right',
      render: (_, u) => (
        <>
          {Math.round(u.allocated_re_per_slot_mean).toLocaleString()} RE/slot
          <div className="muted">{formatPercent(u.allocated_re_share, 1)}</div>
        </>
      ),
    },
    {
      title: 'UE 吞吐率 Throughput',
      key: 'tput',
      align: 'right',
      render: (_, u) => (
        <strong>
          <UeValue ue={u} field="throughput_mbps" digits={2} unit="Mbps" />
        </strong>
      ),
    },
  ];
  return (
    <Table
      rowKey="ue_id"
      size="small"
      columns={columns}
      dataSource={ues}
      pagination={false}
      rowClassName="clickable-row"
      onRow={(u) => ({ onClick: () => onSelect(u.ue_id) })}
    />
  );
}
