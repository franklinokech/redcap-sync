<template>
  <Teleport to="body">
    <!-- Backdrop -->
    <div
        class="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
        @click="emit('close')"
    />

    <!-- Panel -->
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
          class="relative bg-white rounded-2xl shadow-2xl w-full flex flex-col max-h-[90vh]"
          :class="sizeClass"
          @click.stop
      >
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 shrink-0">
          <h2 class="text-lg font-semibold text-gray-900">{{ title }}</h2>
          <button
              @click="emit('close')"
              class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition"
          >
            <XMarkIcon class="w-5 h-5" />
          </button>
        </div>

        <!-- Body -->
        <div class="overflow-y-auto px-6 py-4 flex-1">
          <slot />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import { XMarkIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  title: { type: String, default: '' },
  size:  { type: String, default: 'md' },  // sm | md | lg | xl
})
const emit = defineEmits(['close'])

const sizeClass = computed(() => ({
  sm: 'max-w-sm',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
}[props.size] ?? 'max-w-lg'))
</script>
