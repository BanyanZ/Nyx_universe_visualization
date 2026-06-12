<script setup>
import { useNav } from '@slidev/client'
import { onMounted, onUnmounted } from 'vue'

let teardownDrag = null
const { next, prev } = useNav()

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value))
}

function applySavedPosition(panel) {
  const saved = localStorage.getItem('nyx-slidev-goto-position')
  if (!saved)
    return

  try {
    const pos = JSON.parse(saved)
    if (Number.isFinite(pos.x) && Number.isFinite(pos.y)) {
      panel.style.left = `${clamp(pos.x, 8, window.innerWidth - 120)}px`
      panel.style.top = `${clamp(pos.y, 8, window.innerHeight - 80)}px`
      panel.style.right = 'auto'
      panel.style.transition = 'none'
    }
  }
  catch {
    localStorage.removeItem('nyx-slidev-goto-position')
  }
}

function wireGotoDrag() {
  const panel = document.querySelector('#slidev-goto-dialog')
  if (!panel || panel.dataset.nyxDraggable === 'true')
    return

  panel.dataset.nyxDraggable = 'true'
  applySavedPosition(panel)

  let active = false
  let moved = false
  let startX = 0
  let startY = 0
  let baseX = 0
  let baseY = 0

  const onPointerDown = (event) => {
    if (event.button !== 0)
      return
    if (event.target.closest('input, textarea, button, a'))
      return

    const rect = panel.getBoundingClientRect()
    active = true
    moved = false
    startX = event.clientX
    startY = event.clientY
    baseX = rect.left
    baseY = rect.top
    panel.classList.add('nyx-dragging')
  }

  const onPointerMove = (event) => {
    if (!active)
      return

    const dx = event.clientX - startX
    const dy = event.clientY - startY
    if (Math.abs(dx) + Math.abs(dy) > 4)
      moved = true
    if (!moved)
      return

    event.preventDefault()
    const rect = panel.getBoundingClientRect()
    const x = clamp(baseX + dx, 8, window.innerWidth - rect.width - 8)
    const y = clamp(baseY + dy, 8, window.innerHeight - rect.height - 8)
    panel.style.left = `${x}px`
    panel.style.top = `${y}px`
    panel.style.right = 'auto'
    panel.style.transition = 'none'
  }

  const onPointerUp = () => {
    if (!active)
      return

    active = false
    panel.classList.remove('nyx-dragging')
    const rect = panel.getBoundingClientRect()
    localStorage.setItem('nyx-slidev-goto-position', JSON.stringify({
      x: Math.round(rect.left),
      y: Math.round(rect.top),
    }))
  }

  panel.addEventListener('pointerdown', onPointerDown)
  document.addEventListener('pointermove', onPointerMove)
  document.addEventListener('pointerup', onPointerUp)

  teardownDrag = () => {
    panel.removeEventListener('pointerdown', onPointerDown)
    document.removeEventListener('pointermove', onPointerMove)
    document.removeEventListener('pointerup', onPointerUp)
  }
}

function onEsc(event) {
  if (event.key === 'Escape' && document.fullscreenElement)
    document.exitFullscreen?.()
}

let lastWheelAt = 0

function isInteractiveTarget(target) {
  return target?.closest?.([
    'input',
    'textarea',
    'select',
    'button',
    'a',
    'video',
    'iframe',
    '[contenteditable="true"]',
    '#slidev-goto-dialog',
    '.slidev-code',
    '.nyx-dash',
  ].join(','))
}

function onWheel(event) {
  if (event.ctrlKey || event.metaKey || event.shiftKey)
    return
  if (isInteractiveTarget(event.target))
    return
  if (Math.abs(event.deltaY) < 24 || Math.abs(event.deltaY) < Math.abs(event.deltaX))
    return

  const now = Date.now()
  if (now - lastWheelAt < 620)
    return

  lastWheelAt = now
  event.preventDefault()
  if (event.deltaY > 0)
    next()
  else
    prev()
}

let observer = null

onMounted(() => {
  wireGotoDrag()
  observer = new MutationObserver(wireGotoDrag)
  observer.observe(document.body, { childList: true, subtree: true })
  document.addEventListener('keydown', onEsc, true)
  window.addEventListener('wheel', onWheel, { passive: false })
})

onUnmounted(() => {
  observer?.disconnect()
  teardownDrag?.()
  document.removeEventListener('keydown', onEsc, true)
  window.removeEventListener('wheel', onWheel)
})
</script>

<template>
  <span aria-hidden="true" />
</template>
