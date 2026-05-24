<template>
  <div
      class="flex items-start gap-3 rounded-xl px-4 py-3 text-sm border"
      :class="variantClass"
      role="alert"
  >
    <component :is="icon" class="w-5 h-5 shrink-0 mt-0.5" />
    <div class="flex-1">
      <p v-if="title" class="font-semibold mb-0.5">{{ title }}</p>
      <p>{{ message }}</p>
    </div>
    <button v-if="dismissible" @click="emit('dismiss')" class="opacity-60 hover:opacity-100">
      <XMarkIcon class="w-4 h-4" />
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  InformationCircleIcon,
  ExclamationTriangleIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'

const props = defineProps({
  message:     { type: String,  required: true },
  title:       { type: String,  default: '' },
  variant:     { type: String,  default: 'info' },  // info | success | warning | error
  dismissible: { type: Boolean, default: false },
})
const emit = defineEmits(['dismiss'])

const variantMap = {
  info:    { cls: 'bg-blue-50   border-blue-200   text-blue-800',   icon: InformationCircleIcon },
  success: { cls: 'bg-green-50  border-green-200  text-green-800',  icon: CheckCircleIcon },
  warning: { cls: 'bg-yellow-50 border-yellow-200 text-yellow-800', icon: ExclamationTriangleIcon },
  error:   { cls: 'bg-red-50    border-red-200    text-red-800',    icon: ExclamationCircleIcon },
}

const resolved     = computed(() => variantMap[props.variant] ?? variantMap.info)
const variantClass = computed(() => resolved.value.cls)
const icon         = computed(() => resolved.value.icon)
</script>
