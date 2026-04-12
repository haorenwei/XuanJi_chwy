---
name: echarts-charts
description: Analyze data characteristics and generate appropriate Apache ECharts chart configurations. Covers chart type selection (line, bar, pie, scatter, radar, heatmap, treemap, sankey, gauge, funnel, etc.), data mapping, responsive design, theme customization, and interactive features. Use when the user provides data and needs a chart, asks to visualize data, mentions ECharts, or needs to create dashboards with charts.
---

# ECharts Chart Generation

## Chart Type Selection Decision Tree

When given data, follow this decision tree to select the optimal chart type:

### Step 1: Identify the analytical goal

| Goal | Description | Candidate Charts |
|------|-------------|-----------------|
| **Comparison** | Compare values across categories | Bar, Grouped Bar, Radar |
| **Trend** | Show change over time | Line, Area, Stacked Area |
| **Proportion** | Show parts of a whole | Pie, Donut, Treemap, Sunburst |
| **Distribution** | Show data spread | Scatter, Histogram, Boxplot, Heatmap |
| **Relationship** | Show correlation between variables | Scatter, Bubble, Sankey |
| **Ranking** | Show ordered values | Horizontal Bar, Funnel |
| **Flow** | Show process or transfer | Sankey, Funnel |
| **KPI/Metric** | Show single key value | Gauge, Liquid Fill |
| **Geographic** | Show location-based data | Map, Geo Scatter |

### Step 2: Consider data characteristics

| Data Shape | Recommended |
|-----------|-------------|
| 1 category + 1 value series | Bar / Pie |
| 1 time axis + 1-3 value series | Line |
| 1 time axis + 4+ value series | Stacked Area or split into multiple charts |
| 2 numeric dimensions | Scatter |
| 3 numeric dimensions | Bubble (scatter with size) |
| Hierarchical categories | Treemap / Sunburst |
| Source -> Target flows | Sankey |
| Matrix (row x col x value) | Heatmap |
| Multi-dimensional comparison | Radar |
| Single percentage/progress | Gauge |
| Conversion stages | Funnel |

### Step 3: Data volume considerations

| Volume | Guidance |
|--------|---------|
| < 10 items | Pie/Donut OK; Bar OK |
| 10-50 items | Bar preferred over Pie; Line OK |
| 50-500 items | Line/Scatter; avoid Pie |
| 500-5000 | Enable `large: true` or `sampling`; Scatter OK |
| 5000+ | Use `dataset` + `large: true`; consider `dataZoom`; avoid animations |

## Core Configuration Pattern

Always structure ECharts options using this pattern:

```typescript
import * as echarts from 'echarts'

const option: echarts.EChartsOption = {
  // 1. Title
  title: {
    text: '主标题',
    subtext: '副标题（数据来源/时间范围）',
    left: 'center',
  },
  // 2. Tooltip (always include)
  tooltip: {
    trigger: 'axis', // 'axis' for line/bar, 'item' for pie/scatter
    // formatter for custom display
  },
  // 3. Legend (when multiple series)
  legend: {
    data: ['系列A', '系列B'],
    bottom: 0,
  },
  // 4. Grid (for cartesian charts)
  grid: {
    left: '3%',
    right: '4%',
    bottom: '10%',
    containLabel: true,
  },
  // 5. Axes
  xAxis: { type: 'category', data: [] },
  yAxis: { type: 'value' },
  // 6. Series
  series: [],
}
```

## Key Rules

1. **Always include tooltip** - Charts without tooltip are unusable
2. **Always include title** with descriptive text and data context
3. **Use `dataset`** for complex data transformations instead of inline data
4. **Responsive**: Set container size via CSS, not fixed `width`/`height` in init
5. **Colors**: Use ECharts built-in theme or define a consistent palette
6. **Number formatting**: Use `axisLabel.formatter` for thousands separators, percentages, etc.
7. **Large data**: Enable `large: true`, `sampling: 'lttb'`, and `animation: false` for 1000+ data points
8. **Accessibility**: Include `aria: { enabled: true }` for screen readers

## React Integration Pattern

```tsx
import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

interface ChartProps {
  option: echarts.EChartsOption
  className?: string
}

export function EChart({ option, className = 'h-80 w-full' }: ChartProps) {
  const chartRef = useRef<HTMLDivElement>(null)
  const instanceRef = useRef<echarts.ECharts>()

  useEffect(() => {
    if (!chartRef.current) return
    instanceRef.current = echarts.init(chartRef.current)
    const handleResize = () => instanceRef.current?.resize()
    window.addEventListener('resize', handleResize)
    return () => {
      window.removeEventListener('resize', handleResize)
      instanceRef.current?.dispose()
    }
  }, [])

  useEffect(() => {
    instanceRef.current?.setOption(option, true)
  }, [option])

  return <div ref={chartRef} className={className} />
}
```

## dataZoom for Time Series

For time-series data with many points, always add dataZoom:

```typescript
dataZoom: [
  { type: 'inside', start: 0, end: 100 },
  { type: 'slider', start: 0, end: 100 },
],
```

## Formatting Helpers

```typescript
// Thousands separator
axisLabel: { formatter: (v: number) => v.toLocaleString('zh-CN') }

// Percentage
axisLabel: { formatter: '{value}%' }

// Abbreviation (万/亿)
axisLabel: {
  formatter: (v: number) => {
    if (v >= 1e8) return (v / 1e8).toFixed(1) + '亿'
    if (v >= 1e4) return (v / 1e4).toFixed(1) + '万'
    return v.toString()
  }
}
```

## Detailed References

- For complete chart type catalog with templates, see [chart-catalog.md](chart-catalog.md)
- For data-to-chart mapping examples, see [examples.md](examples.md)
