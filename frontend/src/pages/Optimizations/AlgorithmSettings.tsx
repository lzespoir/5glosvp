import { Descriptions, Form, InputNumber, Radio, Select, Switch } from 'antd';

import type { HyperparameterDefinition, HyperparameterValue } from '../../types/algorithm';
import { formatHyperparameter, hyperparameterError, MAX_EVALUATION_BUDGET } from '../../utils/algorithm';

export type SettingsMode = 'recommended' | 'advanced';

interface Props {
  schema: HyperparameterDefinition[];
  mode: SettingsMode;
  onMode: (m: SettingsMode) => void;
  values: Record<string, HyperparameterValue>;
  onValue: (id: string, v: HyperparameterValue) => void;
  budget: number | null;
  defaultBudget: number;
  onBudget: (b: number | null) => void;
}

function HyperparameterInput({ h, value, onChange }: {
  h: HyperparameterDefinition;
  value: HyperparameterValue | undefined;
  onChange: (v: HyperparameterValue) => void;
}) {
  switch (h.type) {
    case 'boolean':
      return <Switch aria-label={h.id} checked={value === true} onChange={onChange} />;
    case 'categorical':
      return (
        <Select aria-label={h.id} style={{ width: '100%' }} value={value as string | undefined} onChange={onChange}
          options={(h.choices ?? []).map((c) => ({ value: c as string, label: String(c) }))} />
      );
    case 'float':
    case 'integer':
      return (
        <InputNumber aria-label={h.id} style={{ width: '100%' }} value={value as number | undefined}
          step={h.type === 'integer' ? 1 : 0.01} precision={h.type === 'integer' ? 0 : undefined}
          onChange={(v) => v !== null && onChange(v)} />
      );
    default: {
      const unreachable: never = h.type;
      throw new Error(`Unknown hyperparameter type: ${String(unreachable)}`);
    }
  }
}

/** Recommended：全部使用推荐默认值（auto configuration）；Advanced：逐项调整超参数与评价预算。 */
export function AlgorithmSettings({ schema, mode, onMode, values, onValue, budget, defaultBudget, onBudget }: Props) {
  return (
    <div data-testid="algorithm-settings">
      <Radio.Group
        value={mode}
        onChange={(e) => onMode(e.target.value as SettingsMode)}
        optionType="button"
        options={[
          { value: 'recommended', label: '推荐 Recommended' },
          { value: 'advanced', label: '高级 Advanced' },
        ]}
      />
      {mode === 'recommended' ? (
        <Descriptions column={2} size="small" className="section" bordered>
          {schema.map((h) => (
            <Descriptions.Item key={h.id} label={`${h.name_zh} ${h.id}`}>{formatHyperparameter(h.default)}</Descriptions.Item>
          ))}
          <Descriptions.Item label="评价预算 Evaluation Budget">{defaultBudget}</Descriptions.Item>
        </Descriptions>
      ) : (
        <Form layout="vertical" className="section" component="div">
          {schema.map((h) => {
            const err = hyperparameterError(h, values[h.id]);
            return (
              <Form.Item key={h.id} label={`${h.name_zh} ${h.name_en} (${h.id})`} validateStatus={err ? 'error' : undefined}
                help={err ?? (h.description_zh || h.description_en || undefined)}>
                <HyperparameterInput h={h} value={values[h.id]} onChange={(v) => onValue(h.id, v)} />
              </Form.Item>
            );
          })}
          <Form.Item label="评价预算 Evaluation Budget (max_evaluations)"
            help={`平台强制执行；基线不计入；上限 ${MAX_EVALUATION_BUDGET}。Platform-enforced.`}>
            <InputNumber aria-label="Evaluation budget" min={1} max={MAX_EVALUATION_BUDGET} precision={0}
              style={{ width: '100%' }} value={budget} onChange={onBudget} />
          </Form.Item>
        </Form>
      )}
      {schema.length === 0 && (
        <div className="muted section">该算法没有超参数。No hyperparameters.</div>
      )}
    </div>
  );
}
