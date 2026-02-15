import { useEffect, useMemo, useState } from 'react';
import { useSimulationStore } from '../store/simulation-store';

interface BalanceSample {
  step: number;
  // 族群數量
  totalAlive: number;
  explorerCount: number;
  followerCount: number;
  predatorCount: number;
  // 生態指標
  hungerRatio: number;      // 飢餓 agents / 總存活
  lotkaVolterra: number;    // predators / non-predators (0 if no prey)
  nGroups: number;
  // 能量系統
  predatorEnergy: number;
  resourceEnergy: number;
  totalEnergy: number;
}

const MAX_POINTS = 240;

export function SystemBalanceCharts() {
  const state = useSimulationStore((store) => store.state);
  const [history, setHistory] = useState<BalanceSample[]>([]);

  useEffect(() => {
    if (!state) return;

    const HUNGER_THRESHOLD = 30.0;

    let explorerCount = 0;
    let followerCount = 0;
    let predatorCount = 0;
    let predatorEnergy = 0;
    let nonPredatorEnergy = 0;
    let maxAgentEnergy = 1;
    let hungryCount = 0;

    for (let i = 0; i < state.energies.length; i++) {
      const e = state.energies[i];
      const t = state.types[i];
      if (e > maxAgentEnergy) maxAgentEnergy = e;
      if (e < HUNGER_THRESHOLD) hungryCount++;

      if (t === 3) { // PREDATOR
        predatorCount++;
        predatorEnergy += e;
      } else {
        nonPredatorEnergy += e;
        if (t === 0) followerCount++;
        else if (t === 1) explorerCount++;
      }
    }

    const totalAlive = state.energies.length;
    const hungerRatio = totalAlive > 0 ? hungryCount / totalAlive : 0;
    const preyCount = totalAlive - predatorCount;
    const lotkaVolterra = preyCount > 0 ? predatorCount / preyCount : 0;

    let resourceRatioSum = 0;
    for (let i = 0; i < state.resources.length; i++) {
      resourceRatioSum += state.resources[i].amount;
    }
    const resourceEnergy = resourceRatioSum * maxAgentEnergy;
    const totalEnergy = nonPredatorEnergy + predatorEnergy + resourceEnergy;

    const nextSample: BalanceSample = {
      step: state.step,
      totalAlive,
      explorerCount,
      followerCount,
      predatorCount,
      hungerRatio,
      lotkaVolterra,
      nGroups: state.stats.nGroups,
      predatorEnergy,
      resourceEnergy,
      totalEnergy,
    };

    setHistory((prev) => {
      if (prev.length > 0 && prev[prev.length - 1].step === nextSample.step) {
        return prev;
      }
      const next = [...prev, nextSample];
      if (next.length > MAX_POINTS) next.shift();
      return next;
    });
  }, [state]);

  useEffect(() => {
    if (!state) {
      setHistory([]);
    }
  }, [state]);

  const latest = history.length > 0 ? history[history.length - 1] : null;

  return (
    <section className="balance-panel">
      <div className="balance-header">
        <h2>System Balance</h2>
        <p>Realtime trends for population and energy budget</p>
      </div>

      {history.length < 2 ? (
        <div className="balance-empty">Waiting for enough frames to draw charts...</div>
      ) : (
        <>
          <div className="balance-grid">
            <LineChartCard
              title="Total Alive"
              unit="agents"
              color="#27d3a2"
              samples={history}
              valueAccessor={(s) => s.totalAlive}
              latestValue={latest?.totalAlive ?? 0}
            />
            <LineChartCard
              title="Explorer Count"
              unit="agents"
              color="#58c4e0"
              samples={history}
              valueAccessor={(s) => s.explorerCount}
              latestValue={latest?.explorerCount ?? 0}
            />
            <LineChartCard
              title="Follower Count"
              unit="agents"
              color="#a0c878"
              samples={history}
              valueAccessor={(s) => s.followerCount}
              latestValue={latest?.followerCount ?? 0}
            />
            <LineChartCard
              title="Predator Count"
              unit="agents"
              color="#e05c5c"
              samples={history}
              valueAccessor={(s) => s.predatorCount}
              latestValue={latest?.predatorCount ?? 0}
            />
          </div>

          <div className="balance-grid">
            <LineChartCard
              title="Hunger Ratio"
              unit="%"
              color="#ffb347"
              samples={history}
              valueAccessor={(s) => s.hungerRatio * 100}
              latestValue={(latest?.hungerRatio ?? 0) * 100}
            />
            <LineChartCard
              title="Predator / Prey"
              unit="ratio"
              color="#c084e0"
              samples={history}
              valueAccessor={(s) => s.lotkaVolterra}
              latestValue={latest?.lotkaVolterra ?? 0}
            />
            <LineChartCard
              title="Active Groups"
              unit="groups"
              color="#60b0f4"
              samples={history}
              valueAccessor={(s) => s.nGroups}
              latestValue={latest?.nGroups ?? 0}
            />
            <LineChartCard
              title="Total System Energy"
              unit="energy"
              color="#ffb347"
              samples={history}
              valueAccessor={(s) => s.totalEnergy}
              latestValue={latest?.totalEnergy ?? 0}
            />
          </div>
        </>
      )}
    </section>
  );
}

function LineChartCard({
  title,
  unit,
  color,
  samples,
  valueAccessor,
  latestValue,
}: {
  title: string;
  unit: string;
  color: string;
  samples: BalanceSample[];
  valueAccessor: (sample: BalanceSample) => number;
  latestValue: number;
}) {
  const metrics = useMemo(() => {
    const values = samples.map(valueAccessor);
    let min = Number.POSITIVE_INFINITY;
    let max = Number.NEGATIVE_INFINITY;

    for (let i = 0; i < values.length; i++) {
      if (values[i] < min) min = values[i];
      if (values[i] > max) max = values[i];
    }

    if (!Number.isFinite(min) || !Number.isFinite(max)) {
      min = 0;
      max = 1;
    }

    if (Math.abs(max - min) < 1e-6) {
      max += 1;
      min -= 1;
    }

    const width = 1000;
    const height = 260;
    const left = 56;
    const right = 16;
    const top = 14;
    const bottom = 32;
    const plotWidth = width - left - right;
    const plotHeight = height - top - bottom;

    const points = values.map((value, index) => {
      const x = left + (index / Math.max(values.length - 1, 1)) * plotWidth;
      const y = top + ((max - value) / (max - min)) * plotHeight;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    });

    const polylinePoints = points.join(' ');
    const firstPoint = points[0];
    const lastPoint = points[points.length - 1];
    const areaPoints = `${firstPoint} ${polylinePoints} ${lastPoint} ${left + plotWidth},${top + plotHeight} ${left},${top + plotHeight}`;

    return {
      min,
      max,
      width,
      height,
      left,
      right,
      top,
      bottom,
      plotWidth,
      plotHeight,
      polylinePoints,
      areaPoints,
    };
  }, [samples, valueAccessor]);

  return (
    <article className="chart-card">
      <div className="chart-header">
        <div>
          <h3>{title}</h3>
          <p>Last {samples.length} samples</p>
        </div>
        <div className="chart-value" style={{ color }}>
          {latestValue.toFixed(2)}
          <span>{unit}</span>
        </div>
      </div>

      <svg
        className="trend-chart"
        viewBox={`0 0 ${metrics.width} ${metrics.height}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={`${title} trend chart`}
      >
        <text x={12} y={metrics.top + 8} fill="#8ea2b4" fontSize={11}>max</text>
        <text x={12} y={metrics.top + metrics.plotHeight + 4} fill="#8ea2b4" fontSize={11}>min</text>

        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
          const y = metrics.top + ratio * metrics.plotHeight;
          return (
            <line
              key={ratio}
              x1={metrics.left}
              x2={metrics.left + metrics.plotWidth}
              y1={y}
              y2={y}
              stroke="#24303d"
              strokeWidth="1"
            />
          );
        })}

        <polygon points={metrics.areaPoints} fill={color} opacity="0.16" />
        <polyline
          points={metrics.polylinePoints}
          fill="none"
          stroke={color}
          strokeWidth="3"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      </svg>

      <div className="chart-range">
        <span>Min: {metrics.min.toFixed(2)}</span>
        <span>Max: {metrics.max.toFixed(2)}</span>
      </div>
    </article>
  );
}
