# ECharts Examples: Data to Chart

Real-world scenarios demonstrating how to analyze data and select the right chart.

---

## Example 1: Monthly Sales Data

**Input data**:
```
月份: 1月-12月
销售额: [2200, 1800, 2500, 3100, 2800, 3600, 4100, 3800, 3200, 2900, 3500, 4200]
单位: 万元
```

**Analysis**: Single time series -> **Line Chart** (show trend over time)

```typescript
const option: echarts.EChartsOption = {
  title: { text: '2024年月度销售额', subtext: '单位：万元' },
  tooltip: {
    trigger: 'axis',
    formatter: '{b}<br/>{a}: {c} 万元',
  },
  xAxis: {
    type: 'category',
    data: ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'],
  },
  yAxis: {
    type: 'value',
    name: '销售额（万元）',
    axisLabel: { formatter: '{value}' },
  },
  series: [
    {
      name: '销售额',
      type: 'line',
      data: [2200, 1800, 2500, 3100, 2800, 3600, 4100, 3800, 3200, 2900, 3500, 4200],
      smooth: true,
      areaStyle: { opacity: 0.15 },
      markPoint: {
        data: [
          { type: 'max', name: '最高' },
          { type: 'min', name: '最低' },
        ],
      },
      markLine: {
        data: [{ type: 'average', name: '平均' }],
      },
    },
  ],
}
```

**Key decisions**: Added `markPoint` for max/min, `markLine` for average, `areaStyle` for visual emphasis.

---

## Example 2: Department Budget Allocation

**Input data**:
```
部门: 研发, 市场, 运营, 人力, 财务
预算: 350, 200, 150, 100, 80 (万元)
```

**Analysis**: 5 categories, proportion of total -> **Pie Chart** (< 8 categories, showing composition)

```typescript
const option: echarts.EChartsOption = {
  title: { text: '各部门预算分配', left: 'center' },
  tooltip: { trigger: 'item', formatter: '{b}: {c}万元 ({d}%)' },
  legend: { orient: 'vertical', left: 'left' },
  series: [
    {
      type: 'pie',
      radius: ['35%', '65%'],   // Donut style
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { formatter: '{b}\n{d}%' },
      data: [
        { value: 350, name: '研发' },
        { value: 200, name: '市场' },
        { value: 150, name: '运营' },
        { value: 100, name: '人力' },
        { value: 80, name: '财务' },
      ],
    },
  ],
}
```

---

## Example 3: Multi-Product Quarterly Comparison

**Input data**:
```
季度: Q1, Q2, Q3, Q4
产品A: [120, 132, 101, 134]
产品B: [220, 182, 191, 234]
产品C: [150, 232, 201, 154]
```

**Analysis**: Category comparison + time -> **Grouped Bar Chart** (compare across categories and time)

```typescript
const option: echarts.EChartsOption = {
  title: { text: '各产品季度销量对比' },
  tooltip: { trigger: 'axis' },
  legend: { data: ['产品A', '产品B', '产品C'] },
  xAxis: { type: 'category', data: ['Q1', 'Q2', 'Q3', 'Q4'] },
  yAxis: { type: 'value', name: '销量' },
  series: [
    { name: '产品A', type: 'bar', data: [120, 132, 101, 134] },
    { name: '产品B', type: 'bar', data: [220, 182, 191, 234] },
    { name: '产品C', type: 'bar', data: [150, 232, 201, 154] },
  ],
}
```

---

## Example 4: Revenue vs Growth Rate (Dual Axis)

**Input data**:
```
月份: 1月-6月
营收: [500, 600, 550, 700, 800, 750] 万元
增长率: [10, 20, -8.3, 27.3, 14.3, -6.3] %
```

**Analysis**: Two metrics, different scales -> **Dual-axis Chart** (Bar + Line)

```typescript
const option: echarts.EChartsOption = {
  title: { text: '营收与增长率分析' },
  tooltip: { trigger: 'axis' },
  legend: { data: ['营收', '增长率'], bottom: 0 },
  xAxis: { type: 'category', data: ['1月','2月','3月','4月','5月','6月'] },
  yAxis: [
    { type: 'value', name: '营收（万元）', position: 'left' },
    { type: 'value', name: '增长率（%）', position: 'right', axisLabel: { formatter: '{value}%' } },
  ],
  series: [
    {
      name: '营收',
      type: 'bar',
      yAxisIndex: 0,
      data: [500, 600, 550, 700, 800, 750],
      itemStyle: { borderRadius: [4, 4, 0, 0] },
    },
    {
      name: '增长率',
      type: 'line',
      yAxisIndex: 1,
      data: [10, 20, -8.3, 27.3, 14.3, -6.3],
      smooth: true,
    },
  ],
}
```

---

## Example 5: User Conversion Funnel

**Input data**:
```
访问: 10000
注册: 6000
活跃: 4000
付费: 1500
续费: 800
```

**Analysis**: Sequential stages with decreasing values -> **Funnel Chart**

```typescript
const option: echarts.EChartsOption = {
  title: { text: '用户转化漏斗', left: 'center' },
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  series: [
    {
      type: 'funnel',
      left: '10%',
      width: '80%',
      sort: 'descending',
      gap: 2,
      label: { show: true, position: 'inside', formatter: '{b}: {c}' },
      data: [
        { value: 10000, name: '访问' },
        { value: 6000, name: '注册' },
        { value: 4000, name: '活跃' },
        { value: 1500, name: '付费' },
        { value: 800, name: '续费' },
      ],
    },
  ],
}
```

---

## Example 6: Server Metrics Dashboard (Gauge)

**Input data**:
```
CPU使用率: 72%
内存使用率: 85%
```

**Analysis**: Single metric, percentage -> **Gauge Chart**

```typescript
const option: echarts.EChartsOption = {
  series: [
    {
      type: 'gauge',
      center: ['25%', '55%'],
      radius: '80%',
      startAngle: 200,
      endAngle: -20,
      detail: { formatter: '{value}%', fontSize: 18, offsetCenter: [0, '70%'] },
      data: [{ value: 72, name: 'CPU' }],
      axisLine: {
        lineStyle: {
          width: 20,
          color: [[0.3, '#67e0e3'], [0.7, '#37a2da'], [1, '#fd666d']],
        },
      },
      title: { offsetCenter: [0, '90%'] },
    },
    {
      type: 'gauge',
      center: ['75%', '55%'],
      radius: '80%',
      startAngle: 200,
      endAngle: -20,
      detail: { formatter: '{value}%', fontSize: 18, offsetCenter: [0, '70%'] },
      data: [{ value: 85, name: '内存' }],
      axisLine: {
        lineStyle: {
          width: 20,
          color: [[0.3, '#67e0e3'], [0.7, '#37a2da'], [1, '#fd666d']],
        },
      },
      title: { offsetCenter: [0, '90%'] },
    },
  ],
}
```

---

## Example 7: Large Dataset with dataset + dataZoom

**When data comes from API** (e.g., 2000+ daily data points):

```typescript
// data from API: Array<{ date: string, value: number }>
const apiData = await fetchMetrics()

const option: echarts.EChartsOption = {
  dataset: {
    dimensions: ['date', 'value'],
    source: apiData,
  },
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category' },
  yAxis: { type: 'value' },
  dataZoom: [
    { type: 'inside', start: 80, end: 100 },   // default show last 20%
    { type: 'slider', start: 80, end: 100 },
  ],
  series: [
    {
      type: 'line',
      encode: { x: 'date', y: 'value' },
      sampling: 'lttb',
      large: true,
      animation: false,
    },
  ],
}
```

**Key decisions**: `dataset` for clean data binding, `dataZoom` for navigation, `sampling: 'lttb'` + `large: true` for performance.
