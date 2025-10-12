#ifndef RENDER_H
#define RENDER_H

#include <stdbool.h>

struct log_context;
struct nk_context;

/**
 * Describes window creation parameters for the renderer.
 */
struct render_backend_config
{
    const char *title;
    int width;
    int height;
    struct log_context *logger;
};

/**
 * Aggregates runtime state owned by the rendering subsystem.
 */
struct render_backend
{
    struct nk_context *nk;
    void *window;
    int width;
    int height;
    struct log_context *logger;
    bool is_dragging;
    double drag_cursor_start_x;
    double drag_cursor_start_y;
    int drag_window_start_x;
    int drag_window_start_y;
    double drag_cursor_screen_x;
    double drag_cursor_screen_y;
    bool is_resizing;
    double resize_cursor_screen_x;
    double resize_cursor_screen_y;
    int resize_window_start_width;
    int resize_window_start_height;
};

/** Initializes the renderer and associated window/context. */
int render_init(struct render_backend *backend,
                const struct render_backend_config *config);
/** Releases renderer resources and tears down GLFW. */
void render_shutdown(struct render_backend *backend);
/** Pumps window events (non-blocking). */
void render_poll_events(struct render_backend *backend);
/** Begins a new Nuklear frame. */
void render_begin_frame(struct render_backend *backend);
/** Finalizes the frame and swaps buffers. */
void render_end_frame(struct render_backend *backend);
/** Returns true when the user requested the window to close. */
bool render_should_close(const struct render_backend *backend);
/** Accesses the active Nuklear context. */
struct nk_context *render_context(struct render_backend *backend);
/** Retrieves the monotonically increasing GLFW clock. */
float render_time_seconds(void);
/** Returns the current drawable window size. */
void render_window_size(const struct render_backend *backend,
                        int *width,
                        int *height);
/** Requests that the window close after the frame completes. */
void render_window_request_close(struct render_backend *backend);
/** Minimizes the window to the task bar or dock. */
void render_window_minimize(struct render_backend *backend);
/** Toggles between maximized and restored window states. */
void render_window_toggle_maximize(struct render_backend *backend);
/** Reports whether the window is currently maximized. */
bool render_window_is_maximized(const struct render_backend *backend);
/** Begins a manual window drag operation. */
void render_window_begin_drag(struct render_backend *backend);
/** Updates the window position while being dragged. */
void render_window_drag_update(struct render_backend *backend);
/** Ends an active window drag operation. */
void render_window_end_drag(struct render_backend *backend);
/** Begins a manual window resize operation from the bottom-right corner. */
void render_window_begin_resize(struct render_backend *backend);
/** Applies the resize delta while the cursor is dragged. */
void render_window_resize_update(struct render_backend *backend,
                                 int min_width,
                                 int min_height);
/** Ends an active window resize interaction. */
void render_window_end_resize(struct render_backend *backend);

#endif /* RENDER_H */
