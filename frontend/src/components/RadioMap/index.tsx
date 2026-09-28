import { PictureOutlined } from '@ant-design/icons';
import { Empty, Image, Skeleton } from 'antd';
import { useState } from 'react';

import { resolveApiUrl } from '../../api/client';
import type { ArtifactView, ExperimentResponse } from '../../types/experiment';
import { ProvenanceTag } from '../ProvenanceTag';

export const RADIO_MAP_ARTIFACT = 'radio_map.png';

export function findRadioMap(exp: ExperimentResponse): ArtifactView | undefined {
  return exp.artifacts?.find((a) => a.name === RADIO_MAP_ARTIFACT);
}

interface Props {
  experiment: ExperimentResponse;
  /** 图片最大高度（CSS 值），保持原始宽高比 */
  maxHeight?: string;
}

/** Radio Map：保持宽高比、可点击放大、标注实验/场景/数据来源。图片来自 artifact API。 */
export function RadioMap({ experiment, maxHeight = '62vh' }: Props) {
  const artifact = findRadioMap(experiment);
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);

  if (!artifact || failed) {
    return (
      <div className="radio-map radio-map--empty">
        <Empty
          image={<PictureOutlined className="radio-map__empty-icon" />}
          description={failed ? '无线电地图加载失败 / Failed to load radio map' : '暂无无线电地图 / No radio map'}
        />
      </div>
    );
  }

  return (
    <figure className="radio-map">
      <div className="radio-map__canvas" style={{ maxHeight }}>
        {!loaded && <Skeleton.Image active className="radio-map__skeleton" />}
        <Image
          src={resolveApiUrl(artifact.url)}
          alt={`Radio map of ${experiment.experiment_id}`}
          style={{ maxHeight, display: loaded ? undefined : 'none' }}
          className="radio-map__img"
          onLoad={() => setLoaded(true)}
          onError={() => setFailed(true)}
          preview={{ mask: '点击放大 / Click to enlarge' }}
        />
      </div>
      <figcaption className="radio-map__caption">
        <span className="radio-map__id">{experiment.experiment_id}</span>
        <span className="muted">
          {experiment.scenario.name_zh} · {experiment.scenario.scenario_id}
        </span>
        <ProvenanceTag sourceType={experiment.provenance?.source_type} />
      </figcaption>
    </figure>
  );
}
