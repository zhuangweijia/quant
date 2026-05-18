import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import {
  LineChart,
  PieChart,
  BarChart,
  CandlestickChart,
} from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
} from 'echarts/components'

let registered = false

export function registerECharts() {
  if (registered) return
  registered = true
  use([
    CanvasRenderer,
    LineChart,
    PieChart,
    BarChart,
    CandlestickChart,
    TitleComponent,
    TooltipComponent,
    LegendComponent,
    GridComponent,
    DataZoomComponent,
  ])
}
