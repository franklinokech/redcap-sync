<template>
  <Teleport to="body">
    <transition-group
        tag="div"
        class="fixed bottom-6 right-6 z-[100] flex flex-col gap-3 w-80"
        enter-active-class="transition duration-300 ease-out"
        enter-from-class="opacity-0 translate-y-4 scale-95"
        enter-to-class="opacity-100 translate-y-0 scale-100"
        leave-active-class="transition duration-200 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0 scale-95"
    >
      <div
          v-for="t in toasts"
          :key="t.id"
          class="flex items-start gap-3 rounded-xl px-4 py-3 shadow-lg text-sm font-medium border"
          :class="variantClass(t.variant)"
      >
        <component :is="variantIcon(t.variant)" class="w-5 h-5 shrink-0 mt-0.5" />
        <span class="flex-1">{{ t.message }}</span>
        <button @click="remove(t.id)" class="text-current opacity-60 hover:opacity-100 ml-1">
          <XMarkIcon class="w-4 h-4" />
        </button>
      </div>
    </transition-group>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  InformationCircleIcon,
  ExclamationTriangleIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'

const toasts = ref([])
let counter = 0

function show(message, variant = 'info', duration = 4000) {
  const id = ++counter
  toasts.value.push({ id, message, variant })
  setTimeout(() => remove(id), duration)
}

function remove(id) {
  toasts.value = toasts.value.filter(t => t.id !== id)
}

function variantClass(v) {
  return {
    success: 'bg-green-50  border-green-200  text-green-800',
    error:   'bg-red-50    border-red-200    text-red-800',
    warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    info:    'bg-blue-50   border-blue-200   text-blue-800',
  }[v] ?? 'bg-blue-50 border-blue-200 text-blue-800'
}

function variantIcon(v) {
  return {
    success: CheckCircleIcon,
    error:   ExclamationCircleIcon,
    warning: ExclamationTriangleIcon,
    info:    InformationCircleIcon,
  }[v] ?? InformationCircleIcon
}

// Expose show() so parent can call toast.value.show(...)
defineExpose({ show })
</script>
