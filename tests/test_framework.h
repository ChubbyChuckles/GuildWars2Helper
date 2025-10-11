#ifndef TEST_FRAMEWORK_H
#define TEST_FRAMEWORK_H

#include <stddef.h>

struct test_context
{
    int failures;
    int assertions;
    const char *test_name;
};

typedef void (*test_case_fn)(struct test_context *ctx);

struct test_case
{
    const char *name;
    test_case_fn function;
};

void test_run_all(const struct test_case *cases, size_t count);
void test_fail(struct test_context *ctx,
               const char *expression,
               const char *file,
               int line);

#define TEST_ASSERT(ctx, expr)                           \
    do                                                   \
    {                                                    \
        (ctx)->assertions += 1;                          \
        if (!(expr))                                     \
        {                                                \
            test_fail((ctx), #expr, __FILE__, __LINE__); \
            return;                                      \
        }                                                \
    } while (0)

#endif /* TEST_FRAMEWORK_H */
