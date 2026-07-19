import { mount, type VueWrapper } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { wsClient } from '@/utils/websocket'
import { useWebSocket } from './useWebSocket'

vi.mock('@/utils/websocket', () => ({
  wsClient: {
    on: vi.fn(),
    off: vi.fn(),
    send: vi.fn(),
  },
}))

let wrapper: VueWrapper | undefined
let socket: ReturnType<typeof useWebSocket>

const Host = defineComponent({
  setup() {
    socket = useWebSocket()
    return () => h('div')
  },
})

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    wrapper = mount(Host)
  })

  afterEach(() => {
    wrapper?.unmount()
    wrapper = undefined
  })

  it('rolls back a channel when the subscribe send throws and allows retry', () => {
    vi.mocked(wsClient.send)
      .mockImplementationOnce(() => { throw new Error('socket send failed') })
      .mockImplementationOnce(() => undefined)

    expect(() => socket.subscribe('advice:ready')).toThrow('socket send failed')
    expect(socket.channels.value).toEqual([])

    socket.subscribe('advice:ready')
    expect(socket.channels.value).toEqual(['advice:ready'])
    expect(wsClient.send).toHaveBeenCalledTimes(2)
    expect(wsClient.send).toHaveBeenLastCalledWith({
      action: 'subscribe',
      channels: ['advice:ready'],
    })
  })
})
