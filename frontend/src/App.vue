<template>
  <DashboardLayout />
</template>

<script setup>
import DashboardLayout from './DashboardLayout.vue';
</script>

<style>
/* Global styles can remain here if needed, but component-specific styles are in their own files. */
/* We ensure the app takes up the full screen and has no default margin/padding */
html, body, #app {
  margin: 0;
  padding: 0;
  height: 100%;
  width: 100%;
}
</style>