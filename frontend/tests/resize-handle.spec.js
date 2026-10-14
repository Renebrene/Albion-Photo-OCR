// Component test for the draggable panel border: it only reports the cursor
// movement, the owner of the state decides what to do with it.
// @vitest-environment happy-dom

import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { Quasar } from 'quasar'

import ResizeHandle from '../src/components/ResizeHandle.vue'

function mountHandle(direction = 'vertical') {
  return mount(ResizeHandle, {
    props: { direction },
    global: { plugins: [Quasar] },
  })
}

describe('ResizeHandle.vue', () => {
  it('reports the horizontal movement of a vertical border', async () => {
    const wrapper = mountHandle('vertical')

    await wrapper.trigger('pointerdown', { clientX: 100, button: 0 })
    await wrapper.trigger('pointermove', { clientX: 130 })
    await wrapper.trigger('pointermove', { clientX: 140 })
    await wrapper.trigger('pointerup', { clientX: 140 })

    // Two moves: +30 and +10, so the border follows the cursor exactly.
    expect(wrapper.emitted('resize')).toEqual([[30], [10]])
    expect(wrapper.emitted('resize-end')[0][0]).toEqual({ x: 40, y: 0 })
  })

  it('reports the vertical movement of a horizontal border', async () => {
    const wrapper = mountHandle('horizontal')

    await wrapper.trigger('pointerdown', { clientY: 200, button: 0 })
    await wrapper.trigger('pointermove', { clientY: 180 })
    await wrapper.trigger('pointerup', { clientY: 180 })

    expect(wrapper.emitted('resize')).toEqual([[-20]])
  })

  it('ignores movement without a pressed button', async () => {
    const wrapper = mountHandle('vertical')

    await wrapper.trigger('pointermove', { clientX: 500 })

    expect(wrapper.emitted('resize')).toBeUndefined()
  })

  it('ignores a right-click', async () => {
    const wrapper = mountHandle('vertical')

    await wrapper.trigger('pointerdown', { clientX: 10, button: 2 })
    await wrapper.trigger('pointermove', { clientX: 60 })

    expect(wrapper.emitted('resize')).toBeUndefined()
  })

  it('stops reporting after the pointer is released', async () => {
    const wrapper = mountHandle('vertical')

    await wrapper.trigger('pointerdown', { clientX: 10, button: 0 })
    await wrapper.trigger('pointerup', { clientX: 10 })
    await wrapper.trigger('pointermove', { clientX: 300 })

    expect(wrapper.emitted('resize')).toBeUndefined()
  })

  it('can be moved with the keyboard', async () => {
    const wrapper = mountHandle('vertical')

    await wrapper.trigger('keydown', { key: 'ArrowRight' })
    await wrapper.trigger('keydown', { key: 'ArrowLeft' })
    await wrapper.trigger('keydown', { key: 'a' })

    expect(wrapper.emitted('resize')).toEqual([[10], [-10]])
  })
})
