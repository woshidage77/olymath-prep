<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import type { Cube, ProjectionCell, ViewName } from '../types'

const props = defineProps<{
  cubes: Cube[]
  projections: Record<ViewName, ProjectionCell[]>
}>()

const canvasHost = ref<HTMLDivElement | null>(null)
let renderer: THREE.WebGLRenderer | undefined
let camera: THREE.OrthographicCamera | undefined
let scene: THREE.Scene | undefined
let controls: OrbitControls | undefined
let group: THREE.Group | undefined
let groundGrid: THREE.GridHelper | undefined
let frameId = 0
let observer: ResizeObserver | undefined

const viewLabels: Record<ViewName, string> = {
  front: '正面',
  left: '左面',
  top: '上面',
}

function disposeGroup() {
  if (!group) return
  scene?.remove(group)
  group.traverse((object) => {
    if (object instanceof THREE.Mesh || object instanceof THREE.LineSegments) {
      object.geometry.dispose()
      const materials = Array.isArray(object.material) ? object.material : [object.material]
      materials.forEach((material) => material.dispose())
    }
  })
  group = undefined
}

function rebuildCubes() {
  if (!scene) return
  disposeGroup()
  group = new THREE.Group()
  const material = new THREE.MeshStandardMaterial({ color: 0x55a889, roughness: 0.72 })
  const edgeMaterial = new THREE.LineBasicMaterial({ color: 0x18342c })
  for (const cube of props.cubes) {
    const geometry = new THREE.BoxGeometry(0.96, 0.96, 0.96)
    const mesh = new THREE.Mesh(geometry, material)
    mesh.position.set(cube.x, cube.y, cube.z)
    mesh.add(new THREE.LineSegments(new THREE.EdgesGeometry(geometry), edgeMaterial))
    group.add(mesh)
  }
  const box = new THREE.Box3().setFromObject(group)
  const center = box.getCenter(new THREE.Vector3())
  group.position.sub(center)
  if (groundGrid) groundGrid.position.y = box.min.y - center.y - 0.02
  scene.add(group)
  setView('isometric')
}

function setView(view: ViewName | 'isometric') {
  if (!camera || !controls) return
  const positions = {
    isometric: new THREE.Vector3(6, 5, 7),
    front: new THREE.Vector3(0, 0, 9),
    left: new THREE.Vector3(-9, 0, 0),
    top: new THREE.Vector3(0, 9, 0.001),
  }
  camera.position.copy(positions[view])
  camera.up.set(0, 1, 0)
  if (view === 'top') camera.up.set(0, 0, -1)
  controls.target.set(0, 0, 0)
  controls.update()
}

function resize() {
  if (!canvasHost.value || !renderer || !camera) return
  const width = canvasHost.value.clientWidth
  const height = Math.max(canvasHost.value.clientHeight, 360)
  const aspect = width / height
  const size = 3.7
  camera.left = -size * aspect
  camera.right = size * aspect
  camera.top = size
  camera.bottom = -size
  camera.updateProjectionMatrix()
  renderer.setSize(width, height, false)
}

function projectionStyle(cell: ProjectionCell) {
  return {
    gridColumn: cell.col + 1,
    gridRow: cell.row + 1,
  }
}

onMounted(() => {
  if (!canvasHost.value) return
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0xf5f1e8)
  camera = new THREE.OrthographicCamera(-4, 4, 4, -4, 0.1, 100)
  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  canvasHost.value.appendChild(renderer.domElement)
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.enablePan = false
  controls.minZoom = 0.8
  controls.maxZoom = 2.4
  scene.add(new THREE.HemisphereLight(0xffffff, 0x557064, 2.2))
  const light = new THREE.DirectionalLight(0xffffff, 2.8)
  light.position.set(4, 8, 6)
  scene.add(light)
  groundGrid = new THREE.GridHelper(8, 8, 0xb6afa0, 0xd7d0c3)
  scene.add(groundGrid)
  rebuildCubes()
  resize()
  observer = new ResizeObserver(resize)
  observer.observe(canvasHost.value)
  const animate = () => {
    controls?.update()
    if (renderer && scene && camera) renderer.render(scene, camera)
    frameId = requestAnimationFrame(animate)
  }
  animate()
})

watch(() => props.cubes, rebuildCubes)

onBeforeUnmount(() => {
  cancelAnimationFrame(frameId)
  observer?.disconnect()
  controls?.dispose()
  disposeGroup()
  groundGrid?.geometry.dispose()
  if (Array.isArray(groundGrid?.material)) {
    groundGrid.material.forEach((material) => material.dispose())
  } else {
    groundGrid?.material.dispose()
  }
  renderer?.dispose()
  renderer?.domElement.remove()
})
</script>

<template>
  <div class="model-panel">
    <div class="view-toolbar" aria-label="观察方向">
      <button type="button" @click="setView('isometric')">自由观察</button>
      <button
        v-for="labelView in (['front', 'left', 'top'] as ViewName[])"
        :key="labelView"
        type="button"
        @click="setView(labelView)"
      >
        {{ viewLabels[labelView] }}
      </button>
    </div>
    <div ref="canvasHost" class="canvas-host" aria-label="可旋转的小正方体组合模型"></div>
    <p class="interaction-hint">拖动旋转 · 滚轮缩放 · 用固定视角核对投影</p>
  </div>

  <div class="projections" aria-label="三个方向的二维投影">
    <section v-for="(label, view) in viewLabels" :key="view" class="projection-card">
      <h4>{{ label }}看到</h4>
      <div class="projection-grid">
        <span
          v-for="cell in projections[view]"
          :key="cell.col + '-' + cell.row"
          class="projection-cell"
          :class="{ layered: cell.depth > 1 }"
          :style="projectionStyle(cell)"
          :title="cell.depth > 1 ? '这个位置重合 ' + cell.depth + ' 块' : '这个位置可见'"
        >
          <small v-if="cell.depth > 1">{{ cell.depth }}</small>
        </span>
      </div>
    </section>
  </div>
</template>
