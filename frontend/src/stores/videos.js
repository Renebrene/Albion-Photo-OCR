import { defineStore } from 'pinia'

import { fetchVideos } from '../api/client'

// Поколение запросов: сброс (смена фильтра) не должен теряться из-за того,
// что предыдущая страница ещё грузится, а устаревший ответ не должен
// дописываться в новый список.
let generation = 0

export const useVideosStore = defineStore('videos', {
  state: () => ({
    items: [],
    nextCursor: null,
    loading: false,
    error: null,
    query: '',
    dateMode: 'upload',
    dateFrom: '',
    dateTo: '',
    selectedVideoId: null,
  }),

  getters: {
    selectedVideo: (state) =>
      state.items.find((item) => item.video_id === state.selectedVideoId) || null,
  },

  actions: {
    async loadPage({ reset = false } = {}) {
      // Догрузка следующей страницы во время запроса не нужна, а сброс
      // (смена фильтра или дат) терять нельзя: раньше он молча отбрасывался,
      // и пользователь видел выдачу старого фильтра.
      if (this.loading && !reset) return

      const my = ++generation
      this.loading = true
      this.error = null

      if (reset) {
        this.items = []
        this.nextCursor = null
      }

      const cursor = reset ? null : this.nextCursor

      try {
        const page = await fetchVideos({
          limit: 50,
          cursor,
          q: this.query.trim() || null,
          date_from: this.dateFrom || null,
          date_to: this.dateTo || null,
          date_mode: this.dateMode,
        })

        // Пока запрос летел, фильтр сменился: эти строки уже не нужны.
        if (my !== generation) return

        this.items.push(...(page.items || []))
        this.nextCursor = page.next_cursor || null

        if (
          this.selectedVideoId &&
          !this.items.some((item) => item.video_id === this.selectedVideoId)
        ) {
          this.selectedVideoId = null
        }
      } catch (err) {
        if (my === generation) {
          this.error = err.message || 'Не удалось загрузить видео'
        }
      } finally {
        if (my === generation) this.loading = false
      }
    },

    selectVideo(videoId) {
      this.selectedVideoId = this.selectedVideoId === videoId ? null : videoId
    },
  },
})
