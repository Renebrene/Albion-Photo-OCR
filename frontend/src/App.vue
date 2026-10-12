<template>
  <q-layout view="hHh lpR fFf">
    <q-header elevated class="bg-primary text-white">
      <q-toolbar>
        <q-toolbar-title>PhotoBAse</q-toolbar-title>

        <q-tabs align="right" shrink>
          <q-route-tab to="/" label="Фото" exact />
          <q-route-tab to="/technical" label="Технический" exact />
        </q-tabs>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>
