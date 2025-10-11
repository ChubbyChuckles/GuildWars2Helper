#include "test_framework.h"

#include <stdio.h>
#include <stdlib.h>

void test_fail(struct test_context *ctx,
               const char *expression,
               const char *file,
               int line)
{
    if (ctx == NULL)
    {
        return;
    }

    ctx->failures += 1;
    fprintf(stderr,
            "[TEST] %s:%d: %s failed for %s\n",
            file,
            line,
            ctx->test_name,
            expression);
}

void test_run_all(const struct test_case *cases, size_t count)
{
    int total_failures = 0;
    int total_assertions = 0;

    for (size_t i = 0; i < count; ++i)
    {
        struct test_context ctx = {0};
        ctx.test_name = cases[i].name;
        cases[i].function(&ctx);
        total_failures += ctx.failures;
        total_assertions += ctx.assertions;
    }

    if (total_failures == 0)
    {
        printf("All %zu tests passed (%d assertions).\n",
               count,
               total_assertions);
    }
    else
    {
        printf("%d test(s) failed across %zu cases (%d assertions).\n",
               total_failures,
               count,
               total_assertions);
    }

    if (total_failures != 0)
    {
        /* Non-zero exit to signal failure to CI */
        exit(1);
    }
}
