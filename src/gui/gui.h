#ifndef GUI_H
#define GUI_H

#include <stdbool.h>

struct log_context;
struct nk_context;

/**
 * Tracks the interactive state exposed through the control panel.
 */
struct gui_state
{
    float propulsion_level;
    float shield_level;
    float system_temperature;
    bool auto_mode;
    float pulse_phase;
};

/**
 * Configures the GUI layer.
 */
struct gui_config
{
    struct log_context *logger;
};

/**
 * Encapsulates GUI state and shared dependencies.
 */
struct gui_app
{
    struct gui_state state;
    struct log_context *logger;
};

/** Initializes the GUI state. */
int gui_init(struct gui_app *app, const struct gui_config *config);
/** Releases GUI resources. */
void gui_shutdown(struct gui_app *app);
/** Builds the UI for the current frame. */
void gui_render(struct gui_app *app,
                struct nk_context *ctx,
                float delta_seconds);

#endif /* GUI_H */
