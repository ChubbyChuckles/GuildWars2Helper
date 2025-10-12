#include "gui.h"

#include <stdio.h>
#include <math.h>
#include <stddef.h>
#include <string.h>

#include "nk_config.h"
#include "../utils/utils.h"
#include "../render/render.h"

static const char *k_nav_points[] = {
    "Arcology Gate",
    "Fractal Lattice",
    "Sage Conflux",
    "Azure Rift",
    "Eon Relay"};
static const int k_nav_point_count = (int)(sizeof(k_nav_points) / sizeof(k_nav_points[0]));

static const char *k_flight_modes[] = {
    "Cruise",
    "Intercept",
    "Evasion"};

static void push_button_theme(struct nk_context *ctx,
                              struct nk_color normal,
                              struct nk_color hover,
                              struct nk_color active)
{
    nk_style_push_style_item(ctx,
                             &ctx->style.button.normal,
                             nk_style_item_color(normal));
    nk_style_push_style_item(ctx,
                             &ctx->style.button.hover,
                             nk_style_item_color(hover));
    nk_style_push_style_item(ctx,
                             &ctx->style.button.active,
                             nk_style_item_color(active));
    nk_style_push_color(ctx,
                        &ctx->style.button.border_color,
                        nk_rgba(128, 224, 255, 255));
}

static void pop_button_theme(struct nk_context *ctx)
{
    nk_style_pop_color(ctx);
    nk_style_pop_style_item(ctx);
    nk_style_pop_style_item(ctx);
    nk_style_pop_style_item(ctx);
}

int gui_init(struct gui_app *app, const struct gui_config *config)
{
    if (app == NULL || config == NULL)
    {
        return -1;
    }

    memset(app, 0, sizeof(*app));
    app->logger = config->logger;
    app->state.propulsion_level = 0.7f;
    app->state.shield_level = 0.45f;
    app->state.system_temperature = 42.0f;
    app->state.auto_mode = true;
    app->state.pulse_phase = 0.0f;
    app->state.warp_charge = 0.35f;
    app->state.nav_point = 1;
    app->state.flight_mode = 0;
    app->state.signal_noise = 0.12f;
    app->state.anomaly_threshold = 62.0f;
    app->state.drone_deploy = 0.25f;
    app->state.coolant_mix = 0.5f;
    app->state.hud_tint.r = 0.12f;
    app->state.hud_tint.g = 0.85f;
    app->state.hud_tint.b = 0.96f;
    app->state.hud_tint.a = 1.0f;
    app->state.harmonic_channels[0] = 0.35f;
    app->state.harmonic_channels[1] = 0.62f;
    app->state.harmonic_channels[2] = -0.18f;
    app->state.beacon_lock = 0.58f;
    app->state.comm_channel = 7;
    app->state.command_buffer[0] = '\0';
    app->state.drone_online[0] = true;
    app->state.drone_online[1] = false;
    app->state.drone_online[2] = true;
    app->state.stealth_mode = false;
    app->state.spectral_focus = 0.72f;
    app->state.chrono_lag = 3.5f;
    app->state.failsafe_mode = true;
    app->state.cascade_pressure = 0.44f;
    app->state.showcase_tab = 0;
    app->state.menu_choice = 0;
    app->state.context_selection = 0;
    app->state.popup_visible = false;
    app->state.popup_selection = -1;
    app->state.selectable_toggles[0] = true;
    app->state.selectable_toggles[1] = false;
    app->state.selectable_toggles[2] = true;
    app->state.selectable_toggles[3] = false;
    app->state.range_window[0] = 0.2f;
    app->state.range_window[1] = 0.8f;
    app->state.expander_weights[0] = 0.25f;
    app->state.expander_weights[1] = 0.45f;
    app->state.expander_weights[2] = 0.65f;
    app->state.expander_weights[3] = 0.85f;
    app->state.knob_gain = 0.42f;
    app->state.knob_mix = 0.68f;
    strncpy(app->state.filter_buffer, "OMEGA", sizeof(app->state.filter_buffer));
    app->state.filter_buffer[sizeof(app->state.filter_buffer) - 1] = '\0';
    app->state.widget_radio = 1;
    app->state.slider_precision = 42;
    app->state.checklist[0] = true;
    app->state.checklist[1] = false;
    app->state.checklist[2] = true;

    for (int row = 0; row < 3; ++row)
    {
        for (int col = 0; col < 3; ++col)
        {
            app->state.spectrum_matrix[row][col] =
                0.25f + 0.12f * (float)row + 0.07f * (float)col;
        }
    }

    for (int i = 0; i < (int)NK_LEN(app->state.timeline_points); ++i)
    {
        float t = (float)i * 0.35f;
        app->state.timeline_points[i] = 0.5f + 0.5f * cosf(t);
    }

    const char *log_seed =
        "[SYS] Widget lab primed.\n"
        "[SYS] Adjust sliders to sample signal variance.\n";
    strncpy(app->state.multiline_buffer,
            log_seed,
            sizeof(app->state.multiline_buffer));
    app->state.multiline_buffer[sizeof(app->state.multiline_buffer) - 1] = '\0';

    app->state.accent_color = nk_rgba(72, 208, 255, 255);
    app->state.accent_history[0] = nk_rgba(148, 92, 255, 255);
    app->state.accent_history[1] = nk_rgba(56, 236, 176, 255);
    app->state.accent_history[2] = nk_rgba(255, 144, 200, 255);
    app->state.table_selection = 0;
    app->state.dragging_titlebar = false;
    app->state.resizing_window = false;
    app->state.uptime_seconds = 0.0f;
    app->state.smoothed_delta = 1.0f / 60.0f;
    app->state.smoothed_fps = 60.0f;

    app->renderer = config->renderer;

    for (int i = 0; i < (int)NK_LEN(app->state.waveform); ++i)
    {
        float t = (float)i * 0.15f;
        app->state.waveform[i] = 0.5f + 0.5f * sinf(t);
    }

    for (int i = 0; i < (int)NK_LEN(app->state.sequencer); ++i)
    {
        float phase = (float)i / (float)NK_LEN(app->state.sequencer);
        app->state.sequencer[i] = 0.5f + 0.5f * cosf(phase * 2.0f * (float)NK_PI);
    }

    app->state.palette[0] = (struct nk_colorf){.r = 0.18f, .g = 0.52f, .b = 0.92f, .a = 1.0f};
    app->state.palette[1] = (struct nk_colorf){.r = 0.21f, .g = 0.84f, .b = 0.63f, .a = 1.0f};
    app->state.palette[2] = (struct nk_colorf){.r = 0.94f, .g = 0.58f, .b = 0.21f, .a = 1.0f};
    app->state.palette[3] = (struct nk_colorf){.r = 0.92f, .g = 0.27f, .b = 0.58f, .a = 1.0f};

    return 0;
}

void gui_shutdown(struct gui_app *app)
{
    (void)app;
}

void gui_render(struct gui_app *app,
                struct nk_context *ctx,
                float delta_seconds)
{
    if (app == NULL || ctx == NULL)
    {
        return;
    }

    int window_width = 1280;
    int window_height = 720;
    if (app->renderer != NULL)
    {
        render_window_size(app->renderer, &window_width, &window_height);
    }
    if (window_width <= 0)
    {
        window_width = 1280;
    }
    if (window_height <= 0)
    {
        window_height = 720;
    }

    const float titlebar_height = 56.0f;
    const float statusbar_height = 44.0f;
    const float layout_margin_y = 24.0f;
    const float layout_margin_x = fmaxf(12.0f, (float)window_width * 0.0125f);
    const float top_offset = titlebar_height + layout_margin_y;
    const float bottom_offset = statusbar_height + layout_margin_y;
    float usable_height = (float)window_height - top_offset - bottom_offset;
    if (usable_height < 300.0f)
    {
        usable_height = 300.0f;
    }

    if (delta_seconds < 0.0f)
    {
        delta_seconds = 0.0f;
    }
    app->state.uptime_seconds += delta_seconds;
    if (app->state.uptime_seconds < 0.0f)
    {
        app->state.uptime_seconds = 0.0f;
    }

    const float smoothing = 0.12f;
    float clamped_delta = delta_seconds;
    if (clamped_delta < 0.0001f)
    {
        clamped_delta = 0.0001f;
    }
    app->state.smoothed_delta =
        (1.0f - smoothing) * app->state.smoothed_delta + smoothing * clamped_delta;
    float instant_fps = (clamped_delta > 0.0f) ? (1.0f / clamped_delta) : app->state.smoothed_fps;
    app->state.smoothed_fps =
        (1.0f - smoothing) * app->state.smoothed_fps + smoothing * instant_fps;

    app->state.pulse_phase += delta_seconds * 2.5f;
    if (app->state.pulse_phase > 2.0f * (float)NK_PI)
    {
        app->state.pulse_phase -= 2.0f * (float)NK_PI;
    }

    float glow = 0.55f + 0.45f * sinf(app->state.pulse_phase);

    for (int i = 0; i < (int)NK_LEN(app->state.waveform); ++i)
    {
        float t = app->state.pulse_phase * 0.75f + (float)i * 0.2f;
        app->state.waveform[i] = 0.5f + 0.5f * sinf(t);
    }

    for (int i = 0; i < (int)NK_LEN(app->state.sequencer); ++i)
    {
        float t = app->state.pulse_phase * 1.2f + (float)i * 0.6f;
        app->state.sequencer[i] = 0.5f + 0.5f * fabsf(sinf(t));
    }

    for (int row = 0; row < 3; ++row)
    {
        for (int col = 0; col < 3; ++col)
        {
            float base = 0.25f + 0.12f * (float)row + 0.07f * (float)col;
            float ripple = 0.08f * sinf(app->state.pulse_phase + (float)row * 0.9f + (float)col * 0.45f);
            float value = base + ripple;
            value = fmaxf(0.0f, fminf(1.0f, value));
            app->state.spectrum_matrix[row][col] = value;
        }
    }

    for (int i = 0; i < (int)NK_LEN(app->state.timeline_points); ++i)
    {
        float t = app->state.pulse_phase * 0.9f + (float)i * 0.35f;
        app->state.timeline_points[i] = 0.5f + 0.5f * cosf(t);
    }

    const float content_width = (float)window_width - 2.0f * layout_margin_x;
    float column_gap = fmaxf(14.0f, layout_margin_x * 0.85f);
    if (content_width < 720.0f)
    {
        column_gap = fmaxf(12.0f, column_gap * 0.7f);
    }

    const float control_min = 300.0f;
    const float control_max = 420.0f;
    float control_panel_width = (float)window_width * 0.32f;
    control_panel_width = fmaxf(control_min, fminf(control_max, control_panel_width));

    const float diagnostics_min = 220.0f;
    const float diagnostics_max = 320.0f;
    float diagnostics_width = (float)window_width * 0.25f;
    diagnostics_width = fmaxf(diagnostics_min, fminf(diagnostics_max, diagnostics_width));

    float showcase_width = (float)window_width - control_panel_width - diagnostics_width - 2.0f * column_gap - 2.0f * layout_margin_x;
    if (showcase_width < 360.0f)
    {
        float deficit = 360.0f - showcase_width;
        float control_spare = control_panel_width - control_min;
        float diag_spare = diagnostics_width - diagnostics_min;
        float take_control = fminf(control_spare, deficit * 0.5f);
        control_panel_width -= take_control;
        deficit -= take_control;
        float take_diag = fminf(diag_spare, deficit);
        diagnostics_width -= take_diag;
        deficit -= take_diag;
        if (deficit > 0.0f)
        {
            column_gap = fmaxf(10.0f, column_gap - deficit * 0.4f);
        }
        showcase_width = (float)window_width - control_panel_width - diagnostics_width - 2.0f * column_gap - 2.0f * layout_margin_x;
        if (showcase_width < 320.0f)
        {
            showcase_width = 320.0f;
        }
    }

    float panel_x = layout_margin_x;
    struct nk_rect panel_bounds = nk_rect(panel_x,
                                          top_offset,
                                          control_panel_width,
                                          usable_height);

    const float mid_column_x = panel_bounds.x + panel_bounds.w + column_gap;
    const float right_column_x = mid_column_x + diagnostics_width + column_gap;
    const float systems_height = fminf(usable_height * 0.42f, 280.0f);
    float quantum_height = usable_height - systems_height - layout_margin_y;
    if (quantum_height < 220.0f)
    {
        quantum_height = 220.0f;
    }

    if (nk_begin(ctx,
                 "Futuristic Control",
                 panel_bounds,
                 NK_WINDOW_BORDER | NK_WINDOW_MOVABLE | NK_WINDOW_SCALABLE |
                     NK_WINDOW_MINIMIZABLE | NK_WINDOW_TITLE))
    {
        nk_layout_row_dynamic(ctx, 36.0f, 1);
        nk_label(ctx, "Propulsion", NK_TEXT_LEFT);
        nk_layout_row_dynamic(ctx, 26.0f, 1);
        nk_slider_float(ctx,
                        0.0f,
                        &app->state.propulsion_level,
                        1.0f,
                        0.01f);

        nk_layout_row_dynamic(ctx, 36.0f, 1);
        nk_label(ctx, "Shields", NK_TEXT_LEFT);
        nk_layout_row_dynamic(ctx, 26.0f, 1);
        nk_slider_float(ctx,
                        0.0f,
                        &app->state.shield_level,
                        1.0f,
                        0.01f);

        nk_layout_row_dynamic(ctx, 36.0f, 1);
        nk_label(ctx, "Core Temperature (\u00b0C)", NK_TEXT_LEFT);
        nk_layout_row_dynamic(ctx, 30.0f, 1);
        nk_property_float(ctx,
                          "",
                          0.0f,
                          &app->state.system_temperature,
                          120.0f,
                          0.5f,
                          0.2f);

        nk_layout_row_dynamic(ctx, 30.0f, 2);
        bool previous_auto = app->state.auto_mode;
        nk_bool auto_mode = app->state.auto_mode ? nk_true : nk_false;
        nk_checkbox_label(ctx, "Auto Stabilize", &auto_mode);
        app->state.auto_mode = (auto_mode == nk_true);
        if (previous_auto != app->state.auto_mode && app->logger != NULL)
        {
            log_message(app->logger,
                        LOG_LEVEL_INFO,
                        "Auto stabilize %s",
                        app->state.auto_mode ? "enabled" : "disabled");
        }

        nk_layout_row_dynamic(ctx, 30.0f, 1);
        nk_label(ctx, "Warp Charge", NK_TEXT_LEFT);
        nk_size warp_charge = (nk_size)(app->state.warp_charge * 100.0f);
        warp_charge = nk_prog(ctx, warp_charge, 100, nk_true);
        app->state.warp_charge = (float)warp_charge / 100.0f;
        if (nk_widget_is_hovered(ctx))
        {
            nk_tooltip(ctx, "Drag to tune the jump capacitors.");
        }

        const int nav_point_count = k_nav_point_count;
        if (app->state.nav_point < 0 || app->state.nav_point >= nav_point_count)
        {
            app->state.nav_point = 0;
        }

        nk_layout_row_dynamic(ctx, 30.0f, 1);
        nk_label(ctx, "Navigation Solution", NK_TEXT_LEFT);
        if (nk_combo_begin_label(ctx,
                                 k_nav_points[app->state.nav_point],
                                 nk_vec2(280.0f, 200.0f)))
        {
            nk_layout_row_dynamic(ctx, 24.0f, 1);
            for (int i = 0; i < nav_point_count; ++i)
            {
                if (nk_combo_item_label(ctx, k_nav_points[i], NK_TEXT_LEFT))
                {
                    if (app->state.nav_point != i && app->logger != NULL)
                    {
                        log_message(app->logger,
                                    LOG_LEVEL_INFO,
                                    "Navigation solution locked on %s.",
                                    k_nav_points[i]);
                    }
                    app->state.nav_point = i;
                }
            }
            nk_combo_end(ctx);
        }

        nk_layout_row_dynamic(ctx, 26.0f, 3);
        for (int i = 0; i < 3; ++i)
        {
            nk_bool active_mode = app->state.flight_mode == i ? nk_true : nk_false;
            if (nk_option_label(ctx, k_flight_modes[i], active_mode))
            {
                if (app->state.flight_mode != i && app->logger != NULL)
                {
                    log_message(app->logger,
                                LOG_LEVEL_DEBUG,
                                "Flight profile switched to %s mode.",
                                k_flight_modes[i]);
                }
                app->state.flight_mode = i;
            }
        }

        nk_layout_row_dynamic(ctx, 24.0f, 1);
        nk_bool stealth = app->state.stealth_mode ? nk_true : nk_false;
        if (nk_checkbox_label(ctx, "Stealth Envelope", &stealth))
        {
            if (app->state.stealth_mode != (stealth == nk_true) &&
                app->logger != NULL)
            {
                log_message(app->logger,
                            LOG_LEVEL_INFO,
                            "Stealth envelope %s",
                            stealth == nk_true ? "engaged" : "released");
            }
            app->state.stealth_mode = (stealth == nk_true);
        }

        nk_layout_row_dynamic(ctx, 30.0f, 1);
        nk_label(ctx, "Signal Noise Threshold", NK_TEXT_LEFT);
        nk_layout_row_dynamic(ctx, 24.0f, 1);
        nk_slider_float(ctx,
                        0.0f,
                        &app->state.signal_noise,
                        1.0f,
                        0.005f);

        nk_layout_row_dynamic(ctx, 30.0f, 1);
        nk_label(ctx, "Anomaly Gate", NK_TEXT_LEFT);
        nk_layout_row_dynamic(ctx, 24.0f, 1);
        nk_property_float(ctx,
                          "Threshold",
                          0.0f,
                          &app->state.anomaly_threshold,
                          120.0f,
                          0.5f,
                          0.2f);

        nk_layout_row_dynamic(ctx, 30.0f, 1);
        nk_label(ctx, "Coolant Mix", NK_TEXT_LEFT);
        nk_layout_row_dynamic(ctx, 24.0f, 1);
        nk_slider_float(ctx,
                        0.0f,
                        &app->state.coolant_mix,
                        1.0f,
                        0.01f);

        nk_layout_row_dynamic(ctx, 28.0f, 1);
        nk_label(ctx, "Drone Deployment", NK_TEXT_LEFT);
        nk_size deployment = (nk_size)(app->state.drone_deploy * 100.0f);
        deployment = nk_prog(ctx, deployment, 100, nk_true);
        app->state.drone_deploy = (float)deployment / 100.0f;

        static const char *drone_names[] = {
            "Scout",
            "Relay",
            "Defense"};
        nk_layout_row_dynamic(ctx, 24.0f, 3);
        for (int i = 0; i < 3; ++i)
        {
            nk_bool online = app->state.drone_online[i] ? nk_true : nk_false;
            nk_selectable_label(ctx,
                                drone_names[i],
                                NK_TEXT_CENTERED,
                                &online);
            app->state.drone_online[i] = (online == nk_true);
        }

        if (nk_tree_push(ctx, NK_TREE_TAB, "Calibration Matrix", NK_MINIMIZED))
        {
            const char *axes[] = {"Alpha", "Beta", "Gamma"};
            nk_layout_row_dynamic(ctx, 24.0f, 2);
            for (int i = 0; i < 3; ++i)
            {
                nk_label(ctx, axes[i], NK_TEXT_LEFT);
                nk_property_float(ctx,
                                  "",
                                  -2.0f,
                                  &app->state.harmonic_channels[i],
                                  2.0f,
                                  0.01f,
                                  0.005f);
            }
            nk_tree_pop(ctx);
        }

        nk_layout_row_dynamic(ctx, 26.0f, 1);
        nk_label(ctx, "HUD Spectral Tint", NK_TEXT_LEFT);
        nk_layout_row_dynamic(ctx, 150.0f, 1);
        app->state.hud_tint = nk_color_picker(ctx, app->state.hud_tint, NK_RGBA);

        nk_layout_row_dynamic(ctx, 24.0f, 1);
        nk_slider_float(ctx,
                        0.0f,
                        &app->state.hud_tint.a,
                        1.0f,
                        0.01f);

        struct nk_color tint_color = nk_rgba_f(app->state.hud_tint.r,
                                               app->state.hud_tint.g,
                                               app->state.hud_tint.b,
                                               app->state.hud_tint.a);
        nk_style_push_color(ctx, &ctx->style.text.color, tint_color);
        nk_layout_row_dynamic(ctx, 22.0f, 1);
        nk_label(ctx, "Spectral uplink synchronized", NK_TEXT_LEFT);
        nk_style_pop_color(ctx);

        nk_layout_row_dynamic(ctx, 30.0f, 1);
        nk_label(ctx, "Command Uplink", NK_TEXT_LEFT);
        nk_layout_row_dynamic(ctx, 28.0f, 1);
        nk_flags edit_flags = nk_edit_string_zero_terminated(ctx,
                                                             NK_EDIT_FIELD,
                                                             app->state.command_buffer,
                                                             sizeof(app->state.command_buffer),
                                                             nk_filter_default);
        if ((edit_flags & NK_EDIT_COMMITED) != 0 && app->logger != NULL)
        {
            if (app->state.command_buffer[0] != '\0')
            {
                log_message(app->logger,
                            LOG_LEVEL_INFO,
                            "Command uplink received: %s",
                            app->state.command_buffer);
                app->state.command_buffer[0] = '\0';
            }
        }

        struct nk_color normal = nk_rgba_f(0.2f,
                                           0.4f * glow,
                                           0.6f + 0.2f * glow,
                                           1.0f);
        struct nk_color hover = nk_rgba_f(0.3f,
                                          0.5f * glow,
                                          0.8f,
                                          1.0f);
        struct nk_color active = nk_rgba_f(0.4f,
                                           0.8f,
                                           1.0f,
                                           1.0f);

        push_button_theme(ctx, normal, hover, active);
        nk_layout_row_dynamic(ctx, 44.0f, 2);
        if (nk_button_label(ctx, "ENGAGE BOOST"))
        {
            log_message(app->logger,
                        LOG_LEVEL_INFO,
                        "BOOST engaged at %.0f%% thrust.",
                        app->state.propulsion_level * 100.0f);
        }
        if (nk_button_label(ctx, "STABILIZE"))
        {
            log_message(app->logger,
                        LOG_LEVEL_DEBUG,
                        "Stabilizer pulse emitted (shields %.0f%%).",
                        app->state.shield_level * 100.0f);
        }
        pop_button_theme(ctx);

        nk_layout_row_dynamic(ctx, 30.0f, 1);
        nk_prog(ctx,
                (nk_size)(app->state.propulsion_level * 100.0f),
                100,
                nk_false);

        nk_layout_row_dynamic(ctx, 18.0f, 1);
        nk_label(ctx,
                 "Telemetry updates every 250ms",
                 NK_TEXT_LEFT);
    }
    nk_end(ctx);

    if (nk_begin(ctx,
                 "Systems Overview",
                 nk_rect(mid_column_x,
                         top_offset,
                         diagnostics_width,
                         systems_height),
                 NK_WINDOW_BORDER | NK_WINDOW_MOVABLE | NK_WINDOW_TITLE))
    {
        nk_layout_row_dynamic(ctx, 22.0f, 1);
        nk_label(ctx, "Drive Output", NK_TEXT_LEFT);

        float drive_wave = 0.5f + 0.5f * sinf(app->state.pulse_phase * 1.5f);
        nk_layout_row_dynamic(ctx, 80.0f, 1);
        if (nk_chart_begin(ctx, NK_CHART_LINES, 32, 0.0f, 1.0f))
        {
            for (int i = 0; i < 32; ++i)
            {
                float sample = 0.5f +
                               0.5f * sinf(app->state.pulse_phase +
                                           (float)i * 0.3f);
                nk_chart_push(ctx, sample);
            }
            nk_chart_end(ctx);
        }

        nk_layout_row_dynamic(ctx, 22.0f, 1);
        nk_label(ctx, "Reactor Flux", NK_TEXT_LEFT);
        nk_layout_row_dynamic(ctx, 20.0f, 1);
        nk_prog(ctx, (nk_size)(drive_wave * 100.0f), 100, nk_false);

        nk_layout_row_dynamic(ctx, 22.0f, 1);
        nk_label(ctx, "Beacon Lock", NK_TEXT_LEFT);
        nk_layout_row_dynamic(ctx, 18.0f, 1);
        nk_prog(ctx,
                (nk_size)(app->state.beacon_lock * 100.0f),
                100,
                nk_false);

        nk_layout_row_dynamic(ctx, 22.0f, 1);
        nk_property_int(ctx,
                        "Comm Channel",
                        1,
                        &app->state.comm_channel,
                        24,
                        1,
                        0.2f);

        nk_layout_row_dynamic(ctx, 24.0f, 1);
        nk_value_float(ctx,
                       "Signal Noise",
                       app->state.signal_noise);

        nk_layout_row_dynamic(ctx, 26.0f, 2);
        if (nk_button_symbol(ctx, NK_SYMBOL_TRIANGLE_RIGHT))
        {
            app->state.beacon_lock += 0.05f;
            if (app->state.beacon_lock > 1.0f)
            {
                app->state.beacon_lock = 1.0f;
            }
            if (app->logger != NULL)
            {
                log_message(app->logger,
                            LOG_LEVEL_DEBUG,
                            "Beacon lock nudged forward.");
            }
        }
        if (nk_button_symbol(ctx, NK_SYMBOL_MINUS))
        {
            app->state.beacon_lock -= 0.05f;
            if (app->state.beacon_lock < 0.0f)
            {
                app->state.beacon_lock = 0.0f;
            }
        }

        struct nk_color diag_tint = nk_rgba_f(app->state.hud_tint.r,
                                              app->state.hud_tint.g,
                                              app->state.hud_tint.b,
                                              app->state.hud_tint.a);
        nk_style_push_color(ctx, &ctx->style.text.color, diag_tint);
        nk_layout_row_dynamic(ctx, 22.0f, 1);
        nk_labelf(ctx,
                  NK_TEXT_LEFT,
                  "Channel %02d link harmonized",
                  app->state.comm_channel);
        nk_style_pop_color(ctx);
    }
    nk_end(ctx);

    if (nk_begin(ctx,
                 "Toolkit Showcase",
                 nk_rect(right_column_x,
                         top_offset,
                         showcase_width,
                         usable_height),
                 NK_WINDOW_BORDER | NK_WINDOW_MOVABLE | NK_WINDOW_SCALABLE |
                     NK_WINDOW_MINIMIZABLE | NK_WINDOW_TITLE))
    {
        nk_menubar_begin(ctx);
        nk_layout_row_begin(ctx, NK_STATIC, 24.0f, 3);
        nk_layout_row_push(ctx, 110.0f);
        if (nk_menu_begin_label(ctx,
                                "Panels",
                                NK_TEXT_LEFT,
                                nk_vec2(220.0f, 120.0f)))
        {
            nk_layout_row_dynamic(ctx, 24.0f, 1);
            if (nk_menu_item_label(ctx, "Controls", NK_TEXT_LEFT))
            {
                app->state.showcase_tab = 0;
            }
            if (nk_menu_item_label(ctx, "Graphs", NK_TEXT_LEFT))
            {
                app->state.showcase_tab = 1;
            }
            if (nk_menu_item_label(ctx, "Palettes", NK_TEXT_LEFT))
            {
                app->state.showcase_tab = 2;
            }
            if (nk_menu_item_label(ctx, "Widget Lab", NK_TEXT_LEFT))
            {
                app->state.showcase_tab = 3;
            }
            nk_menu_end(ctx);
        }
        nk_layout_row_push(ctx, 150.0f);
        if (nk_menu_begin_label(ctx,
                                "Actions",
                                NK_TEXT_LEFT,
                                nk_vec2(220.0f, 120.0f)))
        {
            nk_layout_row_dynamic(ctx, 24.0f, 1);
            if (nk_menu_item_label(ctx, "Reset Filters", NK_TEXT_LEFT))
            {
                strncpy(app->state.filter_buffer,
                        "OMEGA",
                        sizeof(app->state.filter_buffer));
                app->state.filter_buffer[sizeof(app->state.filter_buffer) - 1] = '\0';
            }
            if (nk_menu_item_label(ctx, "Prime Popup", NK_TEXT_LEFT))
            {
                app->state.popup_visible = true;
                app->state.popup_selection = -1;
            }
            nk_menu_end(ctx);
        }
        nk_layout_row_push(ctx, 110.0f);
        nk_label(ctx, "Toolkit Demo", NK_TEXT_CENTERED);
        nk_layout_row_end(ctx);
        nk_menubar_end(ctx);

        nk_layout_row_dynamic(ctx, 30.0f, 4);
        const char *tab_names[] = {"Controls", "Graphs", "Palettes", "Widget Lab"};
        for (int i = 0; i < 4; ++i)
        {
            nk_bool active = app->state.showcase_tab == i ? nk_true : nk_false;
            if (nk_select_label(ctx, tab_names[i], NK_TEXT_CENTERED, active))
            {
                app->state.showcase_tab = i;
            }
        }
        nk_spacing(ctx, 1);

        if (app->state.showcase_tab == 0)
        {
            nk_layout_row_dynamic(ctx, 24.0f, 1);
            nk_label(ctx, "Gain Sculptor", NK_TEXT_LEFT);
            nk_layout_row_dynamic(ctx, 24.0f, 1);
            app->state.knob_gain = nk_slide_float(ctx,
                                                  0.0f,
                                                  app->state.knob_gain,
                                                  1.0f,
                                                  0.01f);
            nk_layout_row_dynamic(ctx, 24.0f, 1);
            app->state.knob_mix = nk_slide_float(ctx,
                                                 0.0f,
                                                 app->state.knob_mix,
                                                 1.0f,
                                                 0.01f);
            nk_layout_row_dynamic(ctx, 22.0f, 2);
            nk_labelf(ctx,
                      NK_TEXT_LEFT,
                      "Gain %.0f%%",
                      app->state.knob_gain * 100.0f);
            nk_labelf(ctx,
                      NK_TEXT_LEFT,
                      "Mix %.0f%%",
                      app->state.knob_mix * 100.0f);

            nk_layout_row_dynamic(ctx, 24.0f, 2);
            nk_property_float(ctx,
                              "Range Low",
                              0.0f,
                              &app->state.range_window[0],
                              app->state.range_window[1],
                              0.01f,
                              0.002f);
            nk_property_float(ctx,
                              "Range High",
                              app->state.range_window[0],
                              &app->state.range_window[1],
                              1.0f,
                              0.01f,
                              0.002f);
            if (app->state.range_window[0] > app->state.range_window[1])
            {
                app->state.range_window[0] = app->state.range_window[1];
            }

            nk_layout_row_dynamic(ctx, 22.0f, 1);
            nk_labelf(ctx,
                      NK_TEXT_LEFT,
                      "Band %.2f - %.2f",
                      app->state.range_window[0],
                      app->state.range_window[1]);

            nk_layout_row_dynamic(ctx, 28.0f, 2);
            for (int i = 0; i < 4; ++i)
            {
                nk_bool toggle = app->state.selectable_toggles[i] ? nk_true : nk_false;
                const enum nk_symbol_type symbol =
                    (i % 2 == 0) ? NK_SYMBOL_TRIANGLE_UP : NK_SYMBOL_TRIANGLE_DOWN;
                const char *label = (i % 2 == 0) ? "Phase" : "Flux";
                if (nk_selectable_symbol_label(ctx,
                                               symbol,
                                               label,
                                               NK_TEXT_CENTERED,
                                               &toggle))
                {
                    app->state.selectable_toggles[i] = (toggle == nk_true);
                }
            }

            nk_layout_row_dynamic(ctx, 24.0f, 1);
            nk_label(ctx, "Filter Code", NK_TEXT_LEFT);
            nk_edit_string_zero_terminated(ctx,
                                           NK_EDIT_BOX,
                                           app->state.filter_buffer,
                                           sizeof(app->state.filter_buffer),
                                           nk_filter_default);

            nk_layout_row_dynamic(ctx, 26.0f, 2);
            if (nk_button_symbol_label(ctx,
                                       NK_SYMBOL_PLUS,
                                       "Boost",
                                       NK_TEXT_LEFT))
            {
                app->state.popup_visible = true;
            }

            struct nk_rect ctx_bounds = nk_widget_bounds(ctx);
            if (nk_button_symbol_label(ctx,
                                       NK_SYMBOL_TRIANGLE_RIGHT,
                                       "Context",
                                       NK_TEXT_LEFT))
            {
                app->state.context_selection =
                    (app->state.context_selection + 1) % 3;
            }
            if (nk_contextual_begin(ctx,
                                    NK_WINDOW_NO_SCROLLBAR,
                                    nk_vec2(210.0f, 150.0f),
                                    ctx_bounds))
            {
                nk_layout_row_dynamic(ctx, 24.0f, 1);
                if (nk_contextual_item_label(ctx, "Align Beacons", NK_TEXT_LEFT))
                {
                    app->state.context_selection = 0;
                }
                if (nk_contextual_item_label(ctx, "Sync Relays", NK_TEXT_LEFT))
                {
                    app->state.context_selection = 1;
                }
                if (nk_contextual_item_label(ctx, "Purge Buffer", NK_TEXT_LEFT))
                {
                    app->state.context_selection = 2;
                }
                nk_contextual_end(ctx);
            }

            static const char *menu_entries[] = {
                "Diagnostics",
                "Navigation",
                "Intel",
                "Logistics"};
            static const enum nk_symbol_type menu_icons[] = {
                NK_SYMBOL_TRIANGLE_RIGHT,
                NK_SYMBOL_TRIANGLE_DOWN,
                NK_SYMBOL_PLUS,
                NK_SYMBOL_MINUS};
            const int menu_count = (int)NK_LEN(menu_entries);
            if (app->state.menu_choice < 0 || app->state.menu_choice >= menu_count)
            {
                app->state.menu_choice = 0;
            }
            nk_layout_row_dynamic(ctx, 28.0f, 1);
            if (nk_combo_begin_symbol_label(ctx,
                                            menu_entries[app->state.menu_choice],
                                            menu_icons[app->state.menu_choice],
                                            nk_vec2(220.0f, 150.0f)))
            {
                nk_layout_row_dynamic(ctx, 24.0f, 1);
                for (int i = 0; i < menu_count; ++i)
                {
                    if (nk_combo_item_symbol_label(ctx,
                                                   menu_icons[i],
                                                   menu_entries[i],
                                                   NK_TEXT_LEFT))
                    {
                        app->state.menu_choice = i;
                    }
                }
                nk_combo_end(ctx);
            }
            if (nk_widget_is_hovered(ctx))
            {
                nk_tooltipf(ctx,
                            "Active manifest: %s",
                            menu_entries[app->state.menu_choice]);
            }

            nk_layout_row_dynamic(ctx, 24.0f, 1);
            nk_labelf(ctx,
                      NK_TEXT_LEFT,
                      "Context action: %d",
                      app->state.context_selection + 1);

            nk_layout_row_dynamic(ctx, 24.0f, 1);
            nk_labelf(ctx,
                      NK_TEXT_LEFT,
                      "Popup selection: %d",
                      app->state.popup_selection + 1);

            nk_layout_row_dynamic(ctx, 24.0f, 2);
            for (int i = 0; i < 2; ++i)
            {
                const char *label = (i == 0) ? "Aux Telemetry" : "Thermal Buffer";
                nk_bool selectable = app->state.selectable_toggles[2 + i] ? nk_true : nk_false;
                if (nk_selectable_text(ctx,
                                       label,
                                       (int)strlen(label),
                                       NK_TEXT_LEFT,
                                       &selectable))
                {
                    app->state.selectable_toggles[2 + i] = (selectable == nk_true);
                }
            }

            nk_layout_space_begin(ctx, NK_STATIC, 100.0f, 3);
            nk_layout_space_push(ctx, nk_rect(10.0f, 8.0f, 150.0f, 24.0f));
            nk_label(ctx, "Slot Alpha", NK_TEXT_LEFT);
            nk_layout_space_push(ctx, nk_rect(10.0f, 36.0f, 150.0f, 24.0f));
            nk_prog(ctx,
                    (nk_size)(app->state.expander_weights[0] * 100.0f),
                    100,
                    nk_false);
            nk_layout_space_push(ctx, nk_rect(180.0f, 36.0f, 150.0f, 24.0f));
            nk_prog(ctx,
                    (nk_size)(app->state.expander_weights[1] * 100.0f),
                    100,
                    nk_false);
            nk_layout_space_end(ctx);

            if (app->state.popup_visible)
            {
                struct nk_rect popup_rect = nk_rect(60.0f, 80.0f, 240.0f, 200.0f);
                if (nk_popup_begin(ctx,
                                   NK_POPUP_STATIC,
                                   "Command Pulse",
                                   NK_WINDOW_CLOSABLE,
                                   popup_rect))
                {
                    nk_layout_row_dynamic(ctx, 22.0f, 1);
                    nk_label(ctx, "Select command payload", NK_TEXT_LEFT);
                    static const char *popup_items[] = {
                        "Phase Align",
                        "Flux Resync",
                        "Telemetry Burst",
                        "Harmonic Flush"};
                    const int popup_count = (int)NK_LEN(popup_items);
                    nk_layout_row_dynamic(ctx, 24.0f, 1);
                    for (int i = 0; i < popup_count; ++i)
                    {
                        if (nk_button_label(ctx, popup_items[i]))
                        {
                            app->state.popup_selection = i;
                            app->state.popup_visible = false;
                            nk_popup_close(ctx);
                            break;
                        }
                    }
                    nk_layout_row_dynamic(ctx, 28.0f, 1);
                    if (nk_button_label(ctx, "Dismiss"))
                    {
                        app->state.popup_visible = false;
                        nk_popup_close(ctx);
                    }
                    nk_popup_end(ctx);
                }
                else
                {
                    app->state.popup_visible = false;
                }
            }
        }
        else if (app->state.showcase_tab == 1)
        {
            nk_layout_row_dynamic(ctx, 120.0f, 1);
            if (nk_chart_begin_colored(ctx,
                                       NK_CHART_LINES,
                                       nk_rgba(96, 192, 255, 180),
                                       nk_rgba(255, 255, 255, 220),
                                       (int)NK_LEN(app->state.waveform),
                                       0.0f,
                                       1.0f))
            {
                for (int i = 0; i < (int)NK_LEN(app->state.waveform); ++i)
                {
                    nk_chart_push(ctx, app->state.waveform[i]);
                }
                nk_chart_end(ctx);
            }

            nk_layout_row_dynamic(ctx, 80.0f, 1);
            nk_plot(ctx,
                    NK_CHART_COLUMN,
                    app->state.sequencer,
                    (int)NK_LEN(app->state.sequencer),
                    0);

            nk_layout_row_dynamic(ctx, 22.0f, 1);
            nk_labelf(ctx,
                      NK_TEXT_LEFT,
                      "Wave mean: %.2f",
                      app->state.waveform[(int)(NK_LEN(app->state.waveform) / 2)]);

            nk_layout_row_dynamic(ctx, 24.0f, (int)NK_LEN(app->state.expander_weights));
            for (int i = 0; i < (int)NK_LEN(app->state.expander_weights); ++i)
            {
                nk_prog(ctx,
                        (nk_size)(app->state.expander_weights[i] * 100.0f),
                        100,
                        nk_false);
            }

            if (nk_tree_push(ctx, NK_TREE_TAB, "Telemetry Buckets", NK_MINIMIZED))
            {
                nk_layout_row_dynamic(ctx, 24.0f, 2);
                for (int i = 0; i < 4; ++i)
                {
                    nk_labelf(ctx,
                              NK_TEXT_LEFT,
                              "Bucket %d",
                              i + 1);
                    nk_labelf(ctx,
                              NK_TEXT_LEFT,
                              "%.2f",
                              app->state.expander_weights[i]);
                }
                nk_tree_pop(ctx);
            }

            nk_layout_row_dynamic(ctx, 24.0f, 2);
            nk_button_symbol_text(ctx,
                                  NK_SYMBOL_TRIANGLE_RIGHT,
                                  "Advance",
                                  (int)strlen("Advance"),
                                  NK_TEXT_LEFT);
            nk_button_symbol_text(ctx,
                                  NK_SYMBOL_TRIANGLE_LEFT,
                                  "Reverse",
                                  (int)strlen("Reverse"),
                                  NK_TEXT_LEFT);
        }
        else if (app->state.showcase_tab == 2)
        {
            if (nk_group_begin(ctx, "palette_group", NK_WINDOW_BORDER | NK_WINDOW_TITLE))
            {
                for (int i = 0; i < (int)NK_LEN(app->state.palette); ++i)
                {
                    nk_layout_row_dynamic(ctx, 140.0f, 1);
                    struct nk_colorf colorf = app->state.palette[i];
                    if (nk_color_pick(ctx, &colorf, NK_RGBA))
                    {
                        app->state.palette[i] = colorf;
                    }
                    nk_layout_row_dynamic(ctx, 22.0f, 1);
                    struct nk_color color = nk_rgba_f(colorf.r,
                                                      colorf.g,
                                                      colorf.b,
                                                      colorf.a);
                    nk_labelf_colored(ctx,
                                      NK_TEXT_LEFT,
                                      color,
                                      "Swatch %d",
                                      i + 1);
                    nk_value_color_hex(ctx, "Hex", color);
                    nk_spacing(ctx, 1);
                }
                nk_group_end(ctx);
            }

            nk_layout_row_dynamic(ctx, 24.0f, 1);
            nk_labelf_colored_wrap(ctx,
                                   nk_rgba(200, 240, 255, 200),
                                   "Palette drives HUD spectral harmonics.");
        }
        else
        {
            nk_layout_row_dynamic(ctx, 24.0f, 1);
            nk_label(ctx, "Widget Lab", NK_TEXT_LEFT);

            nk_layout_row_dynamic(ctx, 24.0f, 3);
            const char *radio_labels[] = {"Pulse", "Phase", "Drift"};
            for (int i = 0; i < 3; ++i)
            {
                nk_bool active = app->state.widget_radio == i ? nk_true : nk_false;
                if (nk_radio_label(ctx, radio_labels[i], &active) && active == nk_true)
                {
                    app->state.widget_radio = i;
                }
            }

            nk_layout_row_dynamic(ctx, 24.0f, 2);
            nk_slider_int(ctx, 0, &app->state.slider_precision, 100, 1);
            nk_labelf(ctx,
                      NK_TEXT_LEFT,
                      "Precision %d",
                      app->state.slider_precision);

            nk_layout_row_dynamic(ctx, 24.0f, 3);
            const char *check_labels[] = {"Telemetry", "GravLock", "Mirrors"};
            for (int i = 0; i < 3; ++i)
            {
                nk_bool enabled = app->state.checklist[i] ? nk_true : nk_false;
                enabled = nk_check_label(ctx, check_labels[i], enabled);
                app->state.checklist[i] = (enabled == nk_true);
            }

            nk_layout_row_dynamic(ctx, 20.0f, 1);
            nk_label(ctx, "Spectral Matrix", NK_TEXT_LEFT);

            nk_layout_row_template_begin(ctx, 22.0f);
            nk_layout_row_template_push_static(ctx, 90.0f);
            nk_layout_row_template_push_dynamic(ctx);
            nk_layout_row_template_push_dynamic(ctx);
            nk_layout_row_template_push_dynamic(ctx);
            nk_layout_row_template_end(ctx);

            nk_label(ctx, "Band", NK_TEXT_LEFT);
            nk_label(ctx, "Alpha", NK_TEXT_CENTERED);
            nk_label(ctx, "Beta", NK_TEXT_CENTERED);
            nk_label(ctx, "Gamma", NK_TEXT_CENTERED);

            const char *band_names[] = {"Low Band", "Mid Band", "High Band"};
            for (int row = 0; row < 3; ++row)
            {
                nk_layout_row_template_begin(ctx, 24.0f);
                nk_layout_row_template_push_static(ctx, 90.0f);
                nk_layout_row_template_push_dynamic(ctx);
                nk_layout_row_template_push_dynamic(ctx);
                nk_layout_row_template_push_dynamic(ctx);
                nk_layout_row_template_end(ctx);

                nk_bool selected = app->state.table_selection == row ? nk_true : nk_false;
                if (nk_selectable_label(ctx,
                                        band_names[row],
                                        NK_TEXT_LEFT,
                                        &selected) &&
                    selected == nk_true)
                {
                    app->state.table_selection = row;
                }
                for (int col = 0; col < 3; ++col)
                {
                    nk_labelf(ctx,
                              NK_TEXT_CENTERED,
                              "%.2f",
                              app->state.spectrum_matrix[row][col]);
                }
            }

            nk_layout_row_dynamic(ctx, 80.0f, 1);
            nk_plot(ctx,
                    NK_CHART_LINES,
                    app->state.timeline_points,
                    (int)NK_LEN(app->state.timeline_points),
                    0);

            nk_layout_row_dynamic(ctx, 26.0f, 2);
            if (nk_button_color(ctx, app->state.accent_color))
            {
                app->state.accent_history[2] = app->state.accent_history[1];
                app->state.accent_history[1] = app->state.accent_history[0];
                int hue = (app->state.slider_precision * 7) % 255;
                app->state.accent_history[0] = app->state.accent_color;
                app->state.accent_color = nk_rgba((nk_byte)hue,
                                                  (nk_byte)(200 - hue / 2),
                                                  (nk_byte)(128 + hue / 3),
                                                  255);
            }
            nk_value_color_byte(ctx, "Accent", app->state.accent_color);

            nk_layout_row_dynamic(ctx, 22.0f, 1);
            nk_label(ctx, "Accent History", NK_TEXT_LEFT);
            nk_layout_row_dynamic(ctx, 22.0f, 3);
            for (int i = 0; i < 3; ++i)
            {
                nk_value_color_hex(ctx, "", app->state.accent_history[i]);
            }

            nk_layout_row_dynamic(ctx, 22.0f, 1);
            nk_text_wrap(ctx,
                         "Toggle controls to preview how Nuklear widgets respond.",
                         (int)strlen("Toggle controls to preview how Nuklear widgets respond."));

            if (nk_tree_push(ctx, NK_TREE_NODE, "Checklist Summary", NK_MINIMIZED))
            {
                nk_layout_row_dynamic(ctx, 22.0f, 1);
                for (int i = 0; i < 3; ++i)
                {
                    nk_labelf(ctx,
                              NK_TEXT_LEFT,
                              "%s %s",
                              check_labels[i],
                              app->state.checklist[i] ? "ACTIVE" : "IDLE");
                }
                nk_tree_pop(ctx);
            }

            nk_layout_row_dynamic(ctx, 100.0f, 1);
            nk_edit_string_zero_terminated(ctx,
                                           NK_EDIT_MULTILINE,
                                           app->state.multiline_buffer,
                                           sizeof(app->state.multiline_buffer),
                                           nk_filter_default);

            nk_layout_row_dynamic(ctx, 24.0f, 1);
            nk_labelf_colored(ctx,
                              NK_TEXT_LEFT,
                              nk_rgba(180, 220, 255, 200),
                              "Widget radio preset: %d",
                              app->state.widget_radio + 1);

            nk_layout_row_dynamic(ctx, 24.0f, 2);
            nk_bool synth = app->state.selectable_toggles[0] ? nk_true : nk_false;
            if (nk_selectable_symbol_text(ctx,
                                          NK_SYMBOL_TRIANGLE_RIGHT,
                                          "SYNTH",
                                          5,
                                          NK_TEXT_LEFT,
                                          &synth))
            {
                app->state.selectable_toggles[0] = (synth == nk_true);
            }
            nk_bool shield = app->state.selectable_toggles[1] ? nk_true : nk_false;
            if (nk_selectable_symbol_text(ctx,
                                          NK_SYMBOL_TRIANGLE_LEFT,
                                          "SHIELD",
                                          6,
                                          NK_TEXT_LEFT,
                                          &shield))
            {
                app->state.selectable_toggles[1] = (shield == nk_true);
            }

            nk_layout_row_dynamic(ctx, 22.0f, 1);
            nk_text_wrap_colored(ctx,
                                 "Vector timelines auto-cycle using NK_CHART widgets.",
                                 (int)strlen("Vector timelines auto-cycle using NK_CHART widgets."),
                                 nk_rgba(140, 200, 255, 220));
        }
    }
    nk_end(ctx);

    if (nk_begin(ctx,
                 "Quantum Diagnostics",
                 nk_rect(mid_column_x,
                         top_offset + systems_height + layout_margin_y,
                         diagnostics_width,
                         quantum_height),
                 NK_WINDOW_BORDER | NK_WINDOW_MOVABLE | NK_WINDOW_SCALABLE |
                     NK_WINDOW_TITLE))
    {
        if (nk_group_begin(ctx, "Spectral Sweep", NK_WINDOW_BORDER))
        {
            nk_layout_row_dynamic(ctx, 24.0f, 1);
            nk_slider_float(ctx,
                            0.0f,
                            &app->state.spectral_focus,
                            1.0f,
                            0.0025f);

            nk_layout_row_dynamic(ctx, 24.0f, 1);
            nk_property_float(ctx,
                              "Chrono Lag",
                              0.0f,
                              &app->state.chrono_lag,
                              12.0f,
                              0.1f,
                              0.05f);

            nk_layout_row_dynamic(ctx, 20.0f, 1);
            nk_value_float(ctx,
                           "Spectral",
                           app->state.spectral_focus * 100.0f);

            nk_layout_row_dynamic(ctx, 24.0f, 1);
            nk_size cascade = (nk_size)(app->state.cascade_pressure * 100.0f);
            cascade = nk_prog(ctx, cascade, 100, nk_true);
            app->state.cascade_pressure = (float)cascade / 100.0f;

            nk_layout_row_dynamic(ctx, 26.0f, 2);
            if (nk_button_label(ctx, "Pulse Sync"))
            {
                app->state.spectral_focus = fmodf(app->state.spectral_focus + 0.23f, 1.0f);
                if (app->logger != NULL)
                {
                    log_message(app->logger,
                                LOG_LEVEL_DEBUG,
                                "Quantum pulse synchronized.");
                }
            }
            if (nk_button_label(ctx, "Zero Lag"))
            {
                app->state.chrono_lag = 0.0f;
            }
            if (nk_widget_is_hovered(ctx))
            {
                nk_tooltip(ctx, "Maintains resonance under heavy drift.");
            }

            nk_group_end(ctx);
        }

        nk_layout_row_dynamic(ctx, 24.0f, 1);
        nk_bool failsafe = app->state.failsafe_mode ? nk_true : nk_false;
        if (nk_checkbox_label(ctx, "Failsafe Containment", &failsafe))
        {
            app->state.failsafe_mode = (failsafe == nk_true);
        }

        nk_layout_row_dynamic(ctx, 24.0f, 1);
        nk_labelf(ctx,
                  NK_TEXT_LEFT,
                  "Cascade %.1f%%",
                  app->state.cascade_pressure * 100.0f);

        nk_layout_row_dynamic(ctx, 22.0f, 1);
        nk_labelf(ctx,
                  NK_TEXT_LEFT,
                  "Chrono lag %.2fms",
                  app->state.chrono_lag);

        nk_layout_row_dynamic(ctx, 22.0f, 1);
        nk_labelf(ctx,
                  NK_TEXT_LEFT,
                  "Failsafe %s",
                  app->state.failsafe_mode ? "LOCKED" : "DORMANT");
    }
    nk_end(ctx);

    int nav_index = app->state.nav_point;
    if (nav_index < 0 || nav_index >= k_nav_point_count)
    {
        nav_index = 0;
    }
    int flight_index = app->state.flight_mode;
    if (flight_index < 0 || flight_index >= 3)
    {
        flight_index = 0;
    }
    const char *nav_label = k_nav_points[nav_index];
    const char *flight_label = k_flight_modes[flight_index];

    int uptime_minutes = (int)(app->state.uptime_seconds / 60.0f);
    if (uptime_minutes > 99)
    {
        uptime_minutes = 99;
    }
    float uptime_seconds_fraction = fmodf(app->state.uptime_seconds, 60.0f);
    int uptime_seconds_whole = (int)uptime_seconds_fraction;

    char uptime_label[64];
    snprintf(uptime_label,
             sizeof(uptime_label),
             "Uptime %02d:%02d",
             uptime_minutes,
             uptime_seconds_whole);

    char strapline[128];
    snprintf(strapline,
             sizeof(strapline),
             "Route: %s   |   Flight: %s   |   Warp %.0f%%",
             nav_label,
             flight_label,
             app->state.warp_charge * 100.0f);

    char metrics_label[64];
    snprintf(metrics_label,
             sizeof(metrics_label),
             "FPS %05.1f   Δ %.2f ms",
             app->state.smoothed_fps,
             app->state.smoothed_delta * 1000.0f);

    struct nk_color accent_primary = nk_rgba(72, 208, 255, 255);
    struct nk_color accent_secondary = nk_rgba(148, 92, 255, 235);
    int glow_shift = (int)(glow * 45.0f);
    struct nk_color grad_left = nk_rgba(26 + glow_shift,
                                        54 + glow_shift,
                                        108 + glow_shift * 2,
                                        240);
    struct nk_color grad_right = nk_rgba(52 + glow_shift,
                                         124 + glow_shift,
                                         212,
                                         236);
    struct nk_color grad_bottom = nk_rgba(12, 24, 44 + glow_shift, 230);
    struct nk_color grad_bottom_left = nk_rgba(16, 30, 64 + glow_shift, 230);

    struct nk_rect title_bounds = nk_rect(layout_margin_x,
                                          0.0f,
                                          (float)window_width - 2.0f * layout_margin_x,
                                          titlebar_height);
    nk_style_push_style_item(ctx,
                             &ctx->style.window.fixed_background,
                             nk_style_item_color(nk_rgba(0, 0, 0, 0)));
    nk_style_push_color(ctx,
                        &ctx->style.window.background,
                        nk_rgba(0, 0, 0, 0));
    nk_style_push_vec2(ctx, &ctx->style.window.padding, nk_vec2(18.0f, 8.0f));
    nk_style_push_vec2(ctx, &ctx->style.window.spacing, nk_vec2(12.0f, 0.0f));
    if (nk_begin(ctx,
                 "NeonTitleChrome",
                 title_bounds,
                 NK_WINDOW_NO_SCROLLBAR | NK_WINDOW_BACKGROUND))
    {
        struct nk_command_buffer *canvas = nk_window_get_canvas(ctx);
        struct nk_rect bounds = nk_window_get_bounds(ctx);
        nk_fill_rect_multi_color(canvas,
                                 bounds,
                                 grad_left,
                                 grad_right,
                                 grad_bottom,
                                 grad_bottom_left);
        nk_stroke_line(canvas,
                       bounds.x,
                       bounds.y + bounds.h - 2.0f,
                       bounds.x + bounds.w,
                       bounds.y + bounds.h - 2.0f,
                       2.0f,
                       accent_primary);

        struct nk_rect brand_bar = nk_rect(bounds.x + 16.0f,
                                           bounds.y + 6.0f,
                                           6.0f,
                                           bounds.h - 12.0f);
        nk_fill_rect(canvas, brand_bar, 3.0f, accent_primary);

        const float button_width = 40.0f;
        const float content_height = titlebar_height - 18.0f;
        const float brand_width = 200.0f;
        const float metrics_width = 210.0f;
        float padding_x = ctx->style.window.padding.x;
        float spacing_x = ctx->style.window.spacing.x;
        float available_width = bounds.w - 2.0f * padding_x;
        float middle_width = available_width - brand_width - metrics_width - (button_width * 3.0f) - spacing_x * 5.0f;
        if (middle_width < 120.0f)
        {
            middle_width = 120.0f;
        }

        nk_layout_row_begin(ctx, NK_STATIC, content_height, 6);
        nk_layout_row_push(ctx, brand_width);
        nk_label_colored(ctx,
                         "GuildWars2 Helper",
                         NK_TEXT_LEFT,
                         nk_rgba(210, 240, 255, 255));

        nk_layout_row_push(ctx, middle_width);
        nk_label_colored_wrap(ctx,
                              strapline,
                              nk_rgba(180, 228, 255, 235));

        nk_layout_row_push(ctx, metrics_width);
        nk_label_colored(ctx,
                         metrics_label,
                         NK_TEXT_RIGHT,
                         accent_primary);

        struct nk_color btn_normal = nk_rgba(28, 48, 72, 220);
        struct nk_color btn_hover = nk_rgba(64, 112, 172, 240);
        struct nk_color btn_active = nk_rgba(92, 160, 220, 255);
        push_button_theme(ctx, btn_normal, btn_hover, btn_active);

        nk_layout_row_push(ctx, button_width);
        if (nk_button_label(ctx, "-"))
        {
            if (app->renderer != NULL)
            {
                if (app->state.dragging_titlebar)
                {
                    render_window_end_drag(app->renderer);
                    app->state.dragging_titlebar = false;
                }
                if (app->state.resizing_window)
                {
                    render_window_end_resize(app->renderer);
                    app->state.resizing_window = false;
                }
                render_window_minimize(app->renderer);
            }
        }

        nk_layout_row_push(ctx, button_width);
        const char *maximize_label = "[ ]";
        if (app->renderer != NULL && render_window_is_maximized(app->renderer))
        {
            maximize_label = "<>";
        }
        if (nk_button_label(ctx, maximize_label))
        {
            if (app->renderer != NULL)
            {
                if (app->state.dragging_titlebar)
                {
                    render_window_end_drag(app->renderer);
                    app->state.dragging_titlebar = false;
                }
                if (app->state.resizing_window)
                {
                    render_window_end_resize(app->renderer);
                    app->state.resizing_window = false;
                }
                render_window_toggle_maximize(app->renderer);
            }
        }

        nk_layout_row_push(ctx, button_width);
        if (nk_button_label(ctx, "X"))
        {
            if (app->renderer != NULL)
            {
                if (app->state.dragging_titlebar)
                {
                    render_window_end_drag(app->renderer);
                    app->state.dragging_titlebar = false;
                }
                if (app->state.resizing_window)
                {
                    render_window_end_resize(app->renderer);
                    app->state.resizing_window = false;
                }
                render_window_request_close(app->renderer);
            }
        }

        pop_button_theme(ctx);
        nk_layout_row_end(ctx);

        float drag_padding = ctx->style.window.padding.x;
        float drag_start_x = bounds.x + drag_padding + brand_width + 12.0f;
        float drag_width = middle_width;
        struct nk_rect drag_zone = nk_rect(drag_start_x,
                                           bounds.y,
                                           drag_width,
                                           bounds.h);
        const struct nk_input *input = &ctx->input;
        if (app->state.dragging_titlebar)
        {
            if (!nk_input_is_mouse_down(input, NK_BUTTON_LEFT))
            {
                app->state.dragging_titlebar = false;
                if (app->renderer != NULL)
                {
                    render_window_end_drag(app->renderer);
                }
            }
            else if (app->renderer != NULL)
            {
                render_window_drag_update(app->renderer);
            }
        }
        else if (!app->state.resizing_window &&
                 nk_input_is_mouse_hovering_rect(input, drag_zone) &&
                 nk_input_is_mouse_pressed(input, NK_BUTTON_LEFT))
        {
            app->state.dragging_titlebar = true;
            if (app->renderer != NULL)
            {
                render_window_begin_drag(app->renderer);
            }
        }
    }
    nk_end(ctx);
    nk_style_pop_vec2(ctx);
    nk_style_pop_vec2(ctx);
    nk_style_pop_color(ctx);
    nk_style_pop_style_item(ctx);

    struct nk_rect status_bounds = nk_rect(layout_margin_x,
                                           (float)window_height - statusbar_height,
                                           (float)window_width - 2.0f * layout_margin_x,
                                           statusbar_height);
    nk_style_push_style_item(ctx,
                             &ctx->style.window.fixed_background,
                             nk_style_item_color(nk_rgba(0, 0, 0, 0)));
    nk_style_push_color(ctx,
                        &ctx->style.window.background,
                        nk_rgba(0, 0, 0, 0));
    nk_style_push_vec2(ctx, &ctx->style.window.padding, nk_vec2(20.0f, 6.0f));
    nk_style_push_vec2(ctx, &ctx->style.window.spacing, nk_vec2(10.0f, 4.0f));
    if (nk_begin(ctx,
                 "NeonStatusChrome",
                 status_bounds,
                 NK_WINDOW_NO_SCROLLBAR | NK_WINDOW_BACKGROUND))
    {
        struct nk_command_buffer *canvas = nk_window_get_canvas(ctx);
        struct nk_rect bounds = nk_window_get_bounds(ctx);
        nk_fill_rect_multi_color(canvas,
                                 bounds,
                                 nk_rgba(20, 32, 64, 230),
                                 nk_rgba(40, 72, 120, 225),
                                 nk_rgba(16, 24, 40, 225),
                                 nk_rgba(12, 20, 32, 230));
        nk_stroke_line(canvas,
                       bounds.x,
                       bounds.y + 1.5f,
                       bounds.x + bounds.w,
                       bounds.y + 1.5f,
                       2.0f,
                       accent_secondary);

        const float block_height = statusbar_height - 12.0f;
        const float row_height = block_height / 2.0f;
        struct nk_color text_color = nk_rgba(188, 226, 255, 235);

        nk_layout_row_dynamic(ctx, row_height, 4);
        nk_label_colored(ctx, uptime_label, NK_TEXT_LEFT, text_color);
        nk_labelf_colored(ctx,
                          NK_TEXT_LEFT,
                          text_color,
                          "Mode %s",
                          flight_label);
        nk_labelf_colored(ctx,
                          NK_TEXT_LEFT,
                          text_color,
                          "Beacon %.0f%%",
                          app->state.beacon_lock * 100.0f);
        nk_labelf_colored(ctx,
                          NK_TEXT_LEFT,
                          text_color,
                          "Temp %.1f°C",
                          app->state.system_temperature);

        nk_layout_row_dynamic(ctx, row_height, 4);
        nk_prog(ctx,
                (nk_size)(app->state.propulsion_level * 100.0f),
                100,
                nk_false);
        nk_prog(ctx,
                (nk_size)(app->state.shield_level * 100.0f),
                100,
                nk_false);
        nk_prog(ctx,
                (nk_size)(app->state.coolant_mix * 100.0f),
                100,
                nk_false);
        nk_prog(ctx,
                (nk_size)(app->state.signal_noise * 100.0f),
                100,
                nk_false);

        struct nk_rect highlight = nk_rect(bounds.x + bounds.w - 180.0f,
                                           bounds.y + 8.0f,
                                           120.0f,
                                           bounds.h - 16.0f);
        nk_stroke_rect(canvas,
                       highlight,
                       6.0f,
                       2.0f,
                       accent_primary);
        nk_stroke_curve(canvas,
                        highlight.x,
                        highlight.y + highlight.h,
                        highlight.x + highlight.w * 0.35f,
                        highlight.y + highlight.h + 14.0f,
                        highlight.x + highlight.w * 0.65f,
                        highlight.y - 14.0f,
                        highlight.x + highlight.w,
                        highlight.y + highlight.h,
                        1.5f,
                        accent_secondary);

        struct nk_rect resize_handle = nk_rect(bounds.x + bounds.w - 48.0f,
                                               bounds.y + bounds.h - 24.0f,
                                               32.0f,
                                               20.0f);
        nk_fill_triangle(canvas,
                         resize_handle.x,
                         resize_handle.y + resize_handle.h,
                         resize_handle.x + resize_handle.w,
                         resize_handle.y + resize_handle.h,
                         resize_handle.x + resize_handle.w,
                         resize_handle.y,
                         nk_rgba(120, 180, 240, 200));

        const struct nk_input *input = &ctx->input;
        if (app->state.resizing_window)
        {
            if (!nk_input_is_mouse_down(input, NK_BUTTON_LEFT))
            {
                app->state.resizing_window = false;
                if (app->renderer != NULL)
                {
                    render_window_end_resize(app->renderer);
                }
            }
            else if (app->renderer != NULL)
            {
                render_window_resize_update(app->renderer, 960, 600);
            }
        }
        else if (!app->state.dragging_titlebar &&
                 nk_input_is_mouse_hovering_rect(input, resize_handle) &&
                 nk_input_is_mouse_pressed(input, NK_BUTTON_LEFT))
        {
            app->state.resizing_window = true;
            if (app->renderer != NULL)
            {
                render_window_begin_resize(app->renderer);
            }
        }
    }
    nk_end(ctx);
    nk_style_pop_vec2(ctx);
    nk_style_pop_vec2(ctx);
    nk_style_pop_color(ctx);
    nk_style_pop_style_item(ctx);
}
