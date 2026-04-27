import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
export default defineConfig({
    plugins: [react()],
    test: {
        environment: 'jsdom',
        clearMocks: true,
        restoreMocks: true,
    },
    server: {
        port: 5173,
    },
    build: {
        rollupOptions: {
            output: {
                manualChunks: function (id) {
                    if (id.indexOf('node_modules') === -1) {
                        return;
                    }
                    if (id.indexOf('sigma') !== -1 || id.indexOf('graphology') !== -1) {
                        return 'graph-vendor';
                    }
                    if (id.indexOf('react-markdown') !== -1 || id.indexOf('remark-gfm') !== -1) {
                        return 'markdown-vendor';
                    }
                    if (id.indexOf('@tanstack/react-query') !== -1 || id.indexOf('axios') !== -1) {
                        return 'data-vendor';
                    }
                    if (id.indexOf('react-router-dom') !== -1) {
                        return 'router-vendor';
                    }
                    if (id.indexOf('react') !== -1 ||
                        id.indexOf('react-dom') !== -1 ||
                        id.indexOf('@mui/') !== -1 ||
                        id.indexOf('@emotion/') !== -1) {
                        return 'ui-vendor';
                    }
                },
            },
        },
    },
});
