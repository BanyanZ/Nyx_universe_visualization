<script setup>
import { useNav } from '@slidev/client'
import { onMounted, onUnmounted } from 'vue'

let teardownDrag = null
const { next, prev } = useNav()
let canvas = null
let ctx = null
let frameId = 0
let stars = []
let pointerX = 0
let pointerY = 0
let width = 0
let height = 0

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

function resizeCosmos() {
  if (!canvas || !ctx)
    return

  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  width = window.innerWidth
  height = window.innerHeight
  canvas.width = Math.floor(width * dpr)
  canvas.height = Math.floor(height * dpr)
  canvas.style.width = `${width}px`
  canvas.style.height = `${height}px`
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

  const count = Math.min(170, Math.max(92, Math.floor((width * height) / 9000)))
  stars = Array.from({ length: count }, (_, i) => ({
    x: Math.random() * width,
    y: Math.random() * height,
    z: 0.35 + Math.random() * 1.35,
    r: 0.6 + Math.random() * 1.9,
    a: 0.32 + Math.random() * 0.58,
    vx: (Math.random() - 0.5) * 0.12,
    vy: 0.18 + Math.random() * 0.45,
    hue: i % 7 === 0 ? '255, 209, 102' : i % 5 === 0 ? '255, 79, 139' : '111, 247, 223',
  }))
}

function drawCosmos(time = 0) {
  if (!canvas || !ctx)
    return

  const backdrop = ctx.createLinearGradient(0, 0, width, height)
  backdrop.addColorStop(0, '#02030a')
  backdrop.addColorStop(0.42, '#071034')
  backdrop.addColorStop(0.72, '#170828')
  backdrop.addColorStop(1, '#03040c')
  ctx.fillStyle = backdrop
  ctx.fillRect(0, 0, width, height)

  const driftX = (pointerX - 0.5) * 28
  const driftY = (pointerY - 0.5) * 20

  const glow = ctx.createRadialGradient(width * 0.55, height * 0.45, 0, width * 0.55, height * 0.45, Math.max(width, height) * 0.72)
  glow.addColorStop(0, 'rgba(111, 247, 223, 0.13)')
  glow.addColorStop(0.42, 'rgba(69, 183, 255, 0.08)')
  glow.addColorStop(0.72, 'rgba(255, 79, 139, 0.055)')
  glow.addColorStop(1, 'rgba(0, 0, 0, 0)')
  ctx.fillStyle = glow
  ctx.fillRect(0, 0, width, height)

  for (const star of stars) {
    star.x += star.vx * star.z + 0.055
    star.y += star.vy * star.z
    if (star.x > width + 20)
      star.x = -20
    if (star.y > height + 20)
      star.y = -20

    const x = star.x + driftX * star.z
    const y = star.y + driftY * star.z
    const pulse = 0.68 + Math.sin(time * 0.0018 + star.x * 0.025) * 0.32
    ctx.beginPath()
    ctx.fillStyle = `rgba(${star.hue}, ${star.a * pulse})`
    ctx.arc(x, y, star.r * star.z, 0, Math.PI * 2)
    ctx.fill()
  }

  ctx.lineWidth = 0.8
  for (let i = 0; i < stars.length; i++) {
    const a = stars[i]
    const ax = a.x + driftX * a.z
    const ay = a.y + driftY * a.z
    for (let j = i + 1; j < stars.length; j++) {
      const b = stars[j]
      const bx = b.x + driftX * b.z
      const by = b.y + driftY * b.z
      const dx = ax - bx
      const dy = ay - by
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist > 118)
        continue
      const alpha = (1 - dist / 118) * 0.16
      ctx.strokeStyle = `rgba(111, 247, 223, ${alpha})`
      ctx.beginPath()
      ctx.moveTo(ax, ay)
      ctx.lineTo(bx, by)
      ctx.stroke()
    }
  }

  frameId = requestAnimationFrame(drawCosmos)
}

function mountCosmos() {
  canvas = document.createElement('canvas')
  canvas.className = 'nyx-cosmos-canvas'
  canvas.setAttribute('aria-hidden', 'true')
  document.body.prepend(canvas)
  ctx = canvas.getContext('2d')
  resizeCosmos()
  frameId = requestAnimationFrame(drawCosmos)
}

function onPointerMove(event) {
  pointerX = event.clientX / Math.max(window.innerWidth, 1)
  pointerY = event.clientY / Math.max(window.innerHeight, 1)
}

onMounted(() => {
  mountCosmos()
  wireGotoDrag()
  observer = new MutationObserver(wireGotoDrag)
  observer.observe(document.body, { childList: true, subtree: true })
  document.addEventListener('keydown', onEsc, true)
  window.addEventListener('wheel', onWheel, { passive: false })
  window.addEventListener('resize', resizeCosmos)
  window.addEventListener('pointermove', onPointerMove, { passive: true })
})

onUnmounted(() => {
  cancelAnimationFrame(frameId)
  canvas?.remove()
  canvas = null
  ctx = null
  observer?.disconnect()
  teardownDrag?.()
  document.removeEventListener('keydown', onEsc, true)
  window.removeEventListener('wheel', onWheel)
  window.removeEventListener('resize', resizeCosmos)
  window.removeEventListener('pointermove', onPointerMove)
})
</script>

<template>
  <span aria-hidden="true" />
</template>
