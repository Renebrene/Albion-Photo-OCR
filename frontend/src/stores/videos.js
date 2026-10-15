import { defineStore } from 'pinia'

import { fetchVideos } from '../api/client'

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
      if (this.loading) return
      this.loading = true
      this.error = null
      if (reset) {
        this.items = []
        this.nextCursor = null
      }
      try {
        const page = await fetchVideos({
          limit: 50,
          cursor: reset ? null : this.nextCursor,
          q: this.query.trim() || null,
          date_from: this.dateFrom || null,
          date_to: this.dateTo || null,
          date_mode: this.dateMode,
        })
        this.items.push(...(page.items || []))
        this.nextCursor = page.next_cursor || null
        if (this.selectedVideoId && !this.items.some((item) => item.video_id === this.selectedVideoId)) {
          this.selectedVideoId = null
        }
      } catch (err) {
        this.error = err.message || 'Не удалось загрузить видео'
      } finally {
        this.loading = false
      }
    },

    selectVideo(videoId) {
      this.selectedVideoId = this.selectedVideoId === videoId ? null : videoId
    },
  },
})
