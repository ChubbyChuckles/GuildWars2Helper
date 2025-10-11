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
    void *driver;
    int width;
    int height;
    struct log_context *logger;
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

#endif /* RENDER_H */
