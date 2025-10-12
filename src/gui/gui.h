#ifndef GUI_H
#define GUI_H

#include <stdbool.h>

#include "nk_config.h"

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
    float warp_charge;
    int nav_point;
    int flight_mode;
    float signal_noise;
    float anomaly_threshold;
    float drone_deploy;
    float coolant_mix;
    struct nk_colorf hud_tint;
    float harmonic_channels[3];
    float beacon_lock;
    int comm_channel;
    char command_buffer[64];
    bool drone_online[3];
    bool stealth_mode;
    float spectral_focus;
    float chrono_lag;
    bool failsafe_mode;
    float cascade_pressure;
    int showcase_tab;
    int menu_choice;
    int context_selection;
    bool popup_visible;
    int popup_selection;
    bool selectable_toggles[4];
    float waveform[32];
    float sequencer[12];
    float range_window[2];
    float expander_weights[4];
    struct nk_colorf palette[4];
    float knob_gain;
    float knob_mix;
    char filter_buffer[32];
    int widget_radio;
    int slider_precision;
    bool checklist[3];
    float spectrum_matrix[3][3];
    float timeline_points[8];
    char multiline_buffer[256];
    struct nk_color accent_color;
    struct nk_color accent_history[3];
    int table_selection;
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
