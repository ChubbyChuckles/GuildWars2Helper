#ifndef UTILS_H
#define UTILS_H

#include <stdio.h>

/**
 * Defines log severity levels used by the application.
 */
enum log_level
{
    LOG_LEVEL_TRACE = 0,
    LOG_LEVEL_DEBUG,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARN,
    LOG_LEVEL_ERROR
};

/**
 * Log context carrying state for emitting formatted messages.
 */
struct log_context
{
    FILE *stream;
    enum log_level min_level;
};

/**
 * Initializes a logging context that writes to the provided stream.
 */
int log_context_init(struct log_context *ctx,
                     FILE *stream,
                     enum log_level min_level);

/**
 * Updates the minimum severity printed by the logger.
 */
void log_context_set_level(struct log_context *ctx, enum log_level level);

/**
 * Converts a log level into its textual label.
 */
const char *log_level_label(enum log_level level);

/**
 * Emits a formatted log message when the severity passes the filter.
 */
void log_message(struct log_context *ctx,
                 enum log_level level,
                 const char *format,
                 ...);

#endif /* UTILS_H */
