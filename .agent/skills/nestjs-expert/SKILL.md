---
name: nestjs-expert
description: "NestJS framework expert covering module architecture, dependency injection, guards, interceptors, pipes, testing (Jest/Supertest), TypeORM/Mongoose integration, and Passport.js auth. Use when working on NestJS services, resolving DI errors ('Nest can't resolve dependencies'), designing module structure, writing guards or interceptors, debugging TypeORM entities or connections, or implementing JWT authentication — even when the user doesn't explicitly name NestJS. Triggers on phrases like 'guards', 'interceptors', 'DI error', 'module imports', 'passport strategy', 'circular dependency'."
metadata:
  category: framework
  displayName: NestJS Framework Expert
  color: red
  risk: unknown
  source: community
---

# Nest.js Expert

NestJS expertise covering enterprise Node.js architecture, dependency injection patterns, decorators, middleware lifecycle, guards, interceptors, pipes, testing strategies, database integration, and authentication systems.

## When invoked:

0. If a more specialized expert fits better, recommend switching and stop:
   - Pure TypeScript type issues → `typescript-expert` skill
   - React / frontend issues → `react-patterns` or `react-best-practices` skill

   Example: "This is a pure TypeScript type system issue — stopping here. Use the `typescript-expert` skill to continue."

> **Project constraint**: Swagger is NOT used in this project. Never suggest or add `@nestjs/swagger`, `@ApiProperty`, `@ApiOperation`, `@ApiTags`, or any other `@nestjs/swagger` decorators. If a user asks about API documentation, recommend alternatives (e.g. `.http` files, Postman collections) — never Swagger/OpenAPI generation.

1. Detect Nest.js project setup using internal tools first (Read, Grep, Glob)
2. Identify architecture patterns and existing modules
3. Apply appropriate solutions following Nest.js best practices
4. Validate in order: typecheck → unit tests → integration tests → e2e tests

## Domain Coverage

### Module Architecture & Dependency Injection
- Common issues: Circular dependencies, provider scope conflicts, module imports
- Root causes: Incorrect module boundaries, missing exports, improper injection tokens
- Solution priority: 1) Refactor module structure, 2) Use forwardRef, 3) Adjust provider scope
- Tools: `nest generate module`, `nest generate service`
- Resources: [Nest.js Modules](https://docs.nestjs.com/modules), [Providers](https://docs.nestjs.com/providers)

### Controllers & Request Handling
- Common issues: Route conflicts, DTO validation, response serialization
- Root causes: Decorator misconfiguration, missing validation pipes, improper interceptors
- Solution priority: 1) Fix decorator configuration, 2) Add validation, 3) Implement interceptors
- Tools: `nest generate controller`, class-validator, class-transformer
- Resources: [Controllers](https://docs.nestjs.com/controllers), [Validation](https://docs.nestjs.com/techniques/validation)

### Middleware, Guards, Interceptors & Pipes
- Common issues: Execution order, context access, async operations
- Root causes: Incorrect implementation, missing async/await, improper error handling
- Solution priority: 1) Fix execution order, 2) Handle async properly, 3) Implement error handling
- Execution order: Middleware → Guards → Interceptors (before) → Pipes → Route handler → Interceptors (after)
- Resources: [Middleware](https://docs.nestjs.com/middleware), [Guards](https://docs.nestjs.com/guards)

### Testing Strategies (Jest & Supertest)
- Common issues: Mocking dependencies, testing modules, e2e test setup
- Root causes: Improper test module creation, missing mock providers, incorrect async handling
- Solution priority: 1) Fix test module setup, 2) Mock dependencies correctly, 3) Handle async tests
- Tools: `@nestjs/testing`, Jest, Supertest
- Resources: [Testing](https://docs.nestjs.com/fundamentals/testing)

### Database Integration (TypeORM & Mongoose)
- Common issues: Connection management, entity relationships, migrations
- Root causes: Incorrect configuration, missing decorators, improper transaction handling
- Solution priority: 1) Fix configuration, 2) Correct entity setup, 3) Implement transactions
- TypeORM: `@nestjs/typeorm`, entity decorators, repository pattern
- Mongoose: `@nestjs/mongoose`, schema decorators, model injection
- Resources: [TypeORM](https://docs.nestjs.com/techniques/database), [Mongoose](https://docs.nestjs.com/techniques/mongodb)

### Authentication & Authorization (Passport.js)
- Common issues: Strategy configuration, JWT handling, guard implementation
- Root causes: Missing strategy setup, incorrect token validation, improper guard usage
- Solution priority: 1) Configure Passport strategy, 2) Implement guards, 3) Handle JWT properly
- Tools: `@nestjs/passport`, `@nestjs/jwt`, passport strategies
- Resources: [Authentication](https://docs.nestjs.com/security/authentication), [Authorization](https://docs.nestjs.com/security/authorization)

### Configuration & Environment Management
- Common issues: Environment variables, configuration validation, async configuration
- Root causes: Missing config module, improper validation, incorrect async loading
- Solution priority: 1) Setup ConfigModule, 2) Add validation, 3) Handle async config
- Tools: `@nestjs/config`, Joi validation
- Resources: [Configuration](https://docs.nestjs.com/techniques/configuration)

### Error Handling & Logging
- Common issues: Exception filters, logging configuration, error propagation
- Root causes: Missing exception filters, improper logger setup, unhandled promises
- Solution priority: 1) Implement exception filters, 2) Configure logger, 3) Handle all errors
- Tools: Built-in Logger, custom exception filters
- Resources: [Exception Filters](https://docs.nestjs.com/exception-filters), [Logger](https://docs.nestjs.com/techniques/logger)

## Environmental Adaptation

### Detection Phase
Analyze the project to understand:
- Nest.js version and configuration
- Module structure and organization
- Database setup (TypeORM/Mongoose/Prisma)
- Testing framework configuration
- Authentication implementation

Detection commands:
```bash
# Check Nest.js setup
test -f nest-cli.json && echo "Nest.js CLI project detected"
grep -q "@nestjs/core" package.json && echo "Nest.js framework installed"
test -f tsconfig.json && echo "TypeScript configuration found"

# Detect Nest.js version
grep "@nestjs/core" package.json | sed 's/.*"\([0-9\.]*\)".*/Nest.js version: \1/'

# Check database setup
grep -q "@nestjs/typeorm" package.json && echo "TypeORM integration detected"
grep -q "@nestjs/mongoose" package.json && echo "Mongoose integration detected"
grep -q "@prisma/client" package.json && echo "Prisma ORM detected"

# Check authentication
grep -q "@nestjs/passport" package.json && echo "Passport authentication detected"
grep -q "@nestjs/jwt" package.json && echo "JWT authentication detected"

# Analyze module structure
find src -name "*.module.ts" -type f | head -5 | xargs -I {} basename {} .module.ts
```

**Safety note**: Avoid watch/serve processes; use one-shot diagnostics only.

### Adaptation Strategies
- Match existing module patterns and naming conventions
- Follow established testing patterns
- Respect database strategy (repository pattern vs active record)
- Use existing authentication guards and strategies

## Tool Integration

### Diagnostic Tools
```bash
# Analyze module dependencies
nest info

# Compile-check (also catches import errors and DI mismatches)
pnpm build

# Validate module structure
pnpm lint
```

### Fix Validation
```bash
# Verify fixes (validation order)
pnpm build          # 1. Typecheck first
pnpm test           # 2. Run unit tests
pnpm test:e2e       # 3. Run e2e tests if needed
```

**Validation order**: typecheck → unit tests → e2e tests

## Problem-Specific Approaches

For 17 real-world NestJS error messages with GitHub/SO references and step-by-step fixes, read `references/known-issues.md` before diagnosing. It covers DI resolution errors, circular deps, TypeORM connection issues, JWT auth, memory leaks, and more.

## Common Patterns & Solutions

### Module Organization
```typescript
// Feature module pattern
@Module({
  imports: [CommonModule, DatabaseModule],
  controllers: [FeatureController],
  providers: [FeatureService, FeatureRepository],
  exports: [FeatureService] // Export for other modules
})
export class FeatureModule {}
```

### Custom Decorator Pattern
```typescript
// Combine multiple decorators
export const Auth = (...roles: Role[]) => 
  applyDecorators(
    UseGuards(JwtAuthGuard, RolesGuard),
    Roles(...roles),
  );
```

### Testing Pattern
```typescript
// Comprehensive test setup
beforeEach(async () => {
  const module = await Test.createTestingModule({
    providers: [
      ServiceUnderTest,
      {
        provide: DependencyService,
        useValue: mockDependency,
      },
    ],
  }).compile();
  
  service = module.get<ServiceUnderTest>(ServiceUnderTest);
});
```

### Exception Filter Pattern
```typescript
@Catch(HttpException)
export class HttpExceptionFilter implements ExceptionFilter {
  catch(exception: HttpException, host: ArgumentsHost) {
    // Custom error handling
  }
}
```

## Code Review Checklist

Apply this checklist when reviewing NestJS code:

### Module Architecture & Dependency Injection
- [ ] All services are properly decorated with @Injectable()
- [ ] Providers are listed in module's providers array and exports when needed
- [ ] No circular dependencies between modules (check for forwardRef usage)
- [ ] Module boundaries follow domain/feature separation
- [ ] Custom providers use proper injection tokens (avoid string tokens)

### Testing & Mocking
- [ ] Test modules use minimal, focused provider mocks
- [ ] TypeORM repositories use getRepositoryToken(Entity) for mocking
- [ ] No actual database dependencies in unit tests
- [ ] All async operations are properly awaited in tests
- [ ] JwtService and external dependencies are mocked appropriately

### Database Integration (TypeORM Focus)
- [ ] Entity decorators use correct syntax (@Column() not @Column('description'))
- [ ] Connection errors don't crash the entire application
- [ ] Multiple database connections use named connections
- [ ] Database connections have proper error handling and retry logic
- [ ] Entities are properly registered in TypeOrmModule.forFeature()

### Authentication & Security (JWT + Passport)
- [ ] JWT Strategy imports from 'passport-jwt' not 'passport-local'
- [ ] JwtModule secret matches JwtStrategy secretOrKey exactly
- [ ] Authorization headers follow 'Bearer [token]' format
- [ ] Token expiration times are appropriate for use case
- [ ] JWT_SECRET environment variable is properly configured

### Request Lifecycle & Middleware
- [ ] Middleware execution order follows: Middleware → Guards → Interceptors → Pipes
- [ ] Guards properly protect routes and return boolean/throw exceptions
- [ ] Interceptors handle async operations correctly
- [ ] Exception filters catch and transform errors appropriately
- [ ] Pipes validate DTOs with class-validator decorators

### Performance & Optimization
- [ ] Caching is implemented for expensive operations
- [ ] Database queries avoid N+1 problems (use DataLoader pattern)
- [ ] Connection pooling is configured for database connections
- [ ] Memory leaks are prevented (clean up event listeners)
- [ ] Compression middleware is enabled for production

## Decision Trees for Architecture

### Choosing Database ORM
```
Project Requirements:
├─ Need migrations? → TypeORM or Prisma
├─ NoSQL database? → Mongoose
├─ Type safety priority? → Prisma
├─ Complex relations? → TypeORM
└─ Existing database? → TypeORM (better legacy support)
```

### Module Organization Strategy
```
Feature Complexity:
├─ Simple CRUD → Single module with controller + service
├─ Domain logic → Separate domain module + infrastructure
├─ Shared logic → Create shared module with exports
├─ Microservice → Separate app with message patterns
└─ External API → Create client module with HttpModule
```

### Testing Strategy Selection
```
Test Type Required:
├─ Business logic → Unit tests with mocks
├─ API contracts → Integration tests with test database
├─ User flows → E2E tests with Supertest
├─ Performance → Load tests with k6 or Artillery
└─ Security → OWASP ZAP or security middleware tests
```

### Authentication Method
```
Security Requirements:
├─ Stateless API → JWT with refresh tokens
├─ Session-based → Express sessions with Redis
├─ OAuth/Social → Passport with provider strategies
├─ Multi-tenant → JWT with tenant claims
└─ Microservices → Service-to-service auth with mTLS
```

### Caching Strategy
```
Data Characteristics:
├─ User-specific → Redis with user key prefix
├─ Global data → In-memory cache with TTL
├─ Database results → Query result cache
├─ Static assets → CDN with cache headers
└─ Computed values → Memoization decorators
```

## Performance Optimization

### Caching Strategies
- Use built-in cache manager for response caching
- Implement cache interceptors for expensive operations
- Configure TTL based on data volatility
- Use Redis for distributed caching

### Database Optimization
- Use DataLoader pattern for N+1 query problems
- Implement proper indexes on frequently queried fields
- Use query builder for complex queries vs. ORM methods
- Enable query logging in development for analysis

### Request Processing
- Implement compression middleware
- Use streaming for large responses
- Configure proper rate limiting
- Enable clustering for multi-core utilization

## External Resources

### Core Documentation
- [Nest.js Documentation](https://docs.nestjs.com)
- [Nest.js CLI](https://docs.nestjs.com/cli/overview)
- [Nest.js Recipes](https://docs.nestjs.com/recipes)

### Testing Resources
- [Jest Documentation](https://jestjs.io/docs/getting-started)
- [Supertest](https://github.com/visionmedia/supertest)
- [Testing Best Practices](https://github.com/goldbergyoni/javascript-testing-best-practices)

### Database Resources
- [TypeORM Documentation](https://typeorm.io)
- [Mongoose Documentation](https://mongoosejs.com)

### Authentication
- [Passport.js Strategies](http://www.passportjs.org)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)

## Quick Reference Patterns

### Dependency Injection Tokens
```typescript
// Custom provider token
export const CONFIG_OPTIONS = Symbol('CONFIG_OPTIONS');

// Usage in module
@Module({
  providers: [
    {
      provide: CONFIG_OPTIONS,
      useValue: { apiUrl: 'https://api.example.com' }
    }
  ]
})
```

### Global Module Pattern
```typescript
@Global()
@Module({
  providers: [GlobalService],
  exports: [GlobalService],
})
export class GlobalModule {}
```

### Dynamic Module Pattern
```typescript
@Module({})
export class ConfigModule {
  static forRoot(options: ConfigOptions): DynamicModule {
    return {
      module: ConfigModule,
      providers: [
        {
          provide: 'CONFIG_OPTIONS',
          useValue: options,
        },
      ],
    };
  }
}
```

## Success Metrics
- ✅ Problem correctly identified and located in module structure
- ✅ Solution follows Nest.js architectural patterns
- ✅ All tests pass (unit, integration, e2e)
- ✅ No circular dependencies introduced
- ✅ Performance metrics maintained or improved
- ✅ Code follows established project conventions
- ✅ Proper error handling implemented
- ✅ Security best practices applied
- ✅ Documentation updated for API changes

> See also: `backend-testing` skill for unit/integration test patterns in NestJS, `typescript-expert` for deep type-system issues.
