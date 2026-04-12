# ECharts Chart Type Catalog

Each chart type includes: when to use, option template, and key configuration notes.

---

## Line Chart (折线图)

**When**: Time-series trends, continuous data changes.

```typescript
const option: echarts.EChartsOption = {
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'] },
  yAxis: { type: 'value' },
  series: [
    {
      name: 'Series A',
      type: 'line',
      data: [120, 200, 150, 80, 70],
      smooth: true,          // smooth curves (optional)
      // areaStyle: {},       // enable for area chart
    },
  ],
}
```

**Variants**: `smooth: true` for smooth curves, `areaStyle: {}` for area chart, `stack: 'total'` for stacked area.

---

## Bar Chart (柱状图)

**When**: Category comparison, ranking.

```typescript
const option: echarts.EChartsOption = {
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: ['Product A', 'Product B', 'Product C'] },
  yAxis: { type: 'value' },
  series: [
    { name: 'Sales', type: 'bar', data: [120, 200, 150] },
  ],
}
```

**Horizontal bar**: Swap xAxis/yAxis types. Use for long category names or ranking.

```typescript
xAxis: { type: 'value' },
yAxis: { type: 'category', data: categories },
```

**Grouped bar**: Multiple series with same category axis.
**Stacked bar**: Add `stack: 'total'` to each series.

---

## Pie / Donut Chart (饼图/环形图)

**When**: Proportion of whole, < 8 categories.

```typescript
const option: echarts.EChartsOption = {
  tooltip: { trigger: 'item' },
  legend: { orient: 'vertical', left: 'left' },
  series: [
    {
      type: 'pie',
      radius: '60%',           // Donut: radius: ['40%', '70%']
      data: [
        { value: 1048, name: 'Category A' },
        { value: 735, name: 'Category B' },
        { value: 580, name: 'Category C' },
      ],
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.5)' },
      },
      label: { formatter: '{b}: {d}%' },  // show percentage
    },
  ],
}
```

**Donut**: `radius: ['40%', '70%']`. Can place summary text in center via `graphic`.

---

## Scatter Chart (散点图)

**When**: Correlation between two variables, distribution.

```typescript
const option: echarts.EChartsOption = {
  tooltip: {
    trigger: 'item',
    formatter: (p: any) => `${p.seriesName}<br/>${p.value[0]}, ${p.value[1]}`,
  },
  xAxis: { type: 'value', name: 'X Axis Label' },
  yAxis: { type: 'value', name: 'Y Axis Label' },
  series: [
    {
      name: 'Group A',
      type: 'scatter',
      data: [[10, 8.04], [8, 6.95], [13, 7.58]],
      // Bubble: symbolSize: (data) => Math.sqrt(data[2]) * 5
    },
  ],
}
```

**Bubble**: Use third dimension for `symbolSize`.

---

## Radar Chart (雷达图)

**When**: Multi-dimensional comparison (3-8 dimensions), performance profiles.

```typescript
const option: echarts.EChartsOption = {
  tooltip: { trigger: 'item' },
  radar: {
    indicator: [
      { name: 'Sales', max: 6500 },
      { name: 'Admin', max: 16000 },
      { name: 'Tech', max: 30000 },
      { name: 'Support', max: 38000 },
      { name: 'Dev', max: 52000 },
    ],
  },
  series: [
    {
      type: 'radar',
      data: [
        { value: [4200, 3000, 20000, 35000, 50000], name: 'Budget' },
        { value: [5000, 14000, 28000, 26000, 42000], name: 'Actual' },
      ],
    },
  ],
}
```

---

## Heatmap (热力图)

**When**: Matrix data, time-based patterns (day x hour), correlation matrix.

```typescript
const hours = ['12am', '1am', '2am', /* ... */]
const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
// data format: [xIndex, yIndex, value]
const data = [[0, 0, 5], [0, 1, 1], [1, 0, 8], /* ... */]

const option: echarts.EChartsOption = {
  tooltip: { position: 'top' },
  xAxis: { type: 'category', data: hours },
  yAxis: { type: 'category', data: days },
  visualMap: {
    min: 0,
    max: 10,
    calculable: true,
    orient: 'horizontal',
    left: 'center',
    bottom: '0%',
  },
  series: [
    {
      type: 'heatmap',
      data: data,
      label: { show: true },
    },
  ],
}
```

---

## Treemap (矩形树图)

**When**: Hierarchical proportion data, nested categories.

```typescript
const option: echarts.EChartsOption = {
  tooltip: { formatter: '{b}: {c}' },
  series: [
    {
      type: 'treemap',
      data: [
        {
          name: 'Category A',
          value: 100,
          children: [
            { name: 'Sub A1', value: 60 },
            { name: 'Sub A2', value: 40 },
          ],
        },
        { name: 'Category B', value: 80 },
      ],
    },
  ],
}
```

---

## Sankey (桑基图)

**When**: Flow/transfer between nodes, budget allocation, user journey.

```typescript
const option: echarts.EChartsOption = {
  tooltip: { trigger: 'item' },
  series: [
    {
      type: 'sankey',
      data: [
        { name: 'Source A' }, { name: 'Source B' },
        { name: 'Target X' }, { name: 'Target Y' },
      ],
      links: [
        { source: 'Source A', target: 'Target X', value: 100 },
        { source: 'Source A', target: 'Target Y', value: 50 },
        { source: 'Source B', target: 'Target X', value: 80 },
      ],
      emphasis: { focus: 'adjacency' },
    },
  ],
}
```

---

## Gauge (仪表盘)

**When**: Single KPI, progress, real-time metric.

```typescript
const option: echarts.EChartsOption = {
  series: [
    {
      type: 'gauge',
      detail: { formatter: '{value}%', fontSize: 20 },
      data: [{ value: 72, name: 'Completion' }],
      axisLine: {
        lineStyle: {
          width: 15,
          color: [[0.3, '#fd666d'], [0.7, '#37a2da'], [1, '#67e0e3']],
        },
      },
    },
  ],
}
```

---

## Funnel (漏斗图)

**When**: Conversion stages, sequential filtering.

```typescript
const option: echarts.EChartsOption = {
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  series: [
    {
      type: 'funnel',
      left: '10%',
      width: '80%',
      sort: 'descending',
      data: [
        { value: 100, name: 'Visit' },
        { value: 80, name: 'Inquiry' },
        { value: 60, name: 'Order' },
        { value: 40, name: 'Click' },
        { value: 20, name: 'Purchase' },
      ],
    },
  ],
}
```

---

## Boxplot (箱线图)

**When**: Statistical distribution, outlier detection.

```typescript
import { prepareBoxplotData } from 'echarts/extension/dataTool'

const rawData = [
  [850, 740, 900, 1070, 930, 850, 950, 980, 980, 880],
  [960, 940, 960, 940, 880, 800, 850, 880, 900, 840],
]
const boxData = prepareBoxplotData(rawData)

const option: echarts.EChartsOption = {
  xAxis: { type: 'category', data: boxData.axisData },
  yAxis: { type: 'value' },
  series: [
    { type: 'boxplot', data: boxData.boxData },
    { type: 'scatter', data: boxData.outliers },  // outliers
  ],
}
```

---

## Sunburst (旭日图)

**When**: Multi-level hierarchical proportion, drill-down exploration.

```typescript
const option: echarts.EChartsOption = {
  series: [
    {
      type: 'sunburst',
      data: [
        {
          name: 'Root A',
          children: [
            { name: 'Child A1', value: 15 },
            {
              name: 'Child A2',
              children: [
                { name: 'Leaf', value: 5 },
              ],
            },
          ],
        },
      ],
      radius: ['15%', '80%'],
      label: { rotate: 'radial' },
    },
  ],
}
```

---

## Combined / Dual-Axis (组合图/双轴图)

**When**: Two related metrics with different scales (e.g., revenue + growth rate).

```typescript
const option: echarts.EChartsOption = {
  tooltip: { trigger: 'axis' },
  legend: { data: ['Revenue', 'Growth Rate'] },
  xAxis: { type: 'category', data: ['Q1', 'Q2', 'Q3', 'Q4'] },
  yAxis: [
    { type: 'value', name: 'Revenue (万)', position: 'left' },
    { type: 'value', name: 'Growth Rate (%)', position: 'right', axisLabel: { formatter: '{value}%' } },
  ],
  series: [
    { name: 'Revenue', type: 'bar', yAxisIndex: 0, data: [200, 300, 250, 400] },
    { name: 'Growth Rate', type: 'line', yAxisIndex: 1, data: [10, 50, -17, 60] },
  ],
}
```

---

## Theme & Color Palette

Default professional palette:

```typescript
color: ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc']
```

For dashboard consistency, define a shared palette and apply via `echarts.registerTheme()` or pass as `color` option.
