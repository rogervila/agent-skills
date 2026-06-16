---
name: action-pattern
description: Guides agents to implement non-trivial business use cases as one-Action-per-file single-purpose classes or functions with explicit dependencies, context-free inputs, and direct tests.
license: MIT
metadata:
  author: "Roger Vilà"
  repository: "https://github.com/rogervila/agent-skills"
  version: "1.0.2"
  keywords: "ai, agent, skill, action, pattern, use-case, business-logic, single-responsibility, invokable, testable, dependency-injection"
---

# Action Pattern

Use this skill to design, implement, or review non-trivial application use cases as Actions: single-purpose classes or functions that live in their own files, receive dependencies explicitly, accept context-free runtime data, execute one business operation, and can be tested directly.

This skill solves the "fat controller" and "god service" problem by moving business workflows out of entry points and broad services into small, named units such as `RegisterUserAction`, `ProcessPaymentAction`, or `SendInvitationAction`.

## Activation Criteria

Use this skill when the task is to:

- Create, refactor, or review a business operation, use case, command, application service, or workflow.
- Move logic out of a controller, route handler, CLI command, job, listener, or broad service.
- Organize business rules that coordinate repositories, services, notifications, events, transactions, or external systems.
- Make a use case independently testable without running through HTTP, CLI, queue, or framework entry points.

Do not use this skill when the task is only to:

- Build infrastructure or reusable utilities such as HTTP clients, parsers, formatters, validators, serializers, or SDK wrappers.
- Add a pure data transformation with no dependencies or side effects.
- Implement a simple read-only query, repository lookup, or trivial CRUD passthrough.
- Build UI components, routing glue, schema definitions, migrations, or framework configuration unless they call an Action.

If the request could mean either a business use case or a utility/infrastructure helper, inspect the surrounding code first. Ask for clarification only when the operation boundary or intended side effects remain unclear.

## Required Inputs And Prerequisites

Before acting, inspect the repository for:

- Existing Action, use-case, command, service, CQRS, or domain-layer conventions.
- Language, framework, dependency-injection container, test framework, and file naming style.
- Existing file organization for Actions, while still enforcing one Action definition per source file for new or refactored Actions.
- The entry point that will call the Action and the plain runtime data it can pass.
- Dependencies the Action needs, such as repositories, gateways, services, other Actions, clocks, event buses, or transaction managers.
- Existing tests for the same behavior, plus any domain rules or error cases that must be preserved.

Ask the user before implementing when required business rules, transaction boundaries, side effects, authorization expectations, or return values cannot be inferred safely from the codebase.

## Quick Start Workflow

1. **Classify** the requested behavior as a business operation, utility, query, or entry-point concern.
2. **Locate** the smallest single operation the Action should own and name it with the `Action` suffix.
3. **Design** a context-free input shape and explicit return value. Do not pass framework request, response, session, or CLI objects into the Action.
4. **Inject** dependencies through the constructor for classes, or explicit parameters for functions.
5. **Implement** the Action in its own source file. Do not group multiple Actions in one module, even when Actions are plain functions.
6. **Call** the Action from thin entry points such as controllers, routes, commands, jobs, and listeners.
7. **Test** the Action directly with mocked dependencies and run the relevant test suite.

## 1. Core Principles

### Single Responsibility

Each Action performs **exactly one** business operation. If you need a second public method, you need a second Action.

- ✅ `CreateUserAction` — creates a user
- ✅ `SendInvitationAction` — sends an invitation
- ❌ `UserAction` — vague, likely does too many things
- ❌ `UserService` with `create()`, `update()`, `delete()` — this is a service, not an Action

### One Action Per File

Every Action must be defined in its own source file or module. This rule is mandatory for function-based Actions as well as class-based Actions.

- ✅ `src/actions/auth/register-user.action.ts` exports `registerUserAction` and no other Action.
- ✅ `src/actions/auth/verify-email.action.ts` exports `verifyEmailAction` and no other Action.
- ❌ `src/actions/auth/user.actions.ts` exports `registerUserAction`, `verifyEmailAction`, and `resetPasswordAction` from one grouped file.
- ❌ `src/actions/auth/actions.ts` collects several business operations because they share dependencies or types.

Barrel files such as `src/actions/auth/index.ts` may re-export Actions from separate files, but they must not define Actions. Shared types may live next to a single Action when only that Action uses them; if multiple Actions need the same type or helper, move it to a separate type, utility, or domain-service file instead of grouping Actions together.

The only acceptable same-file non-Action code is supporting code owned by that one Action, such as a private helper, a local input type, or a language-standard inline test block. Do not define a second Action in the file.

### Business Logic Only

Actions encapsulate **business logic**. Non-business reusable code must be delegated to libraries, utilities, or infrastructure services.

| Belongs in an Action | Belongs in a Library/Utility |
|---|---|
| Create a user account | Hash a password |
| Process a subscription payment | Format a currency string |
| Generate an invoice | Send an HTTP request |
| Apply a discount to an order | Parse a CSV file |
| Transfer funds between accounts | Validate an email format |

### Context Independence

Actions must not depend on their calling context. They do not know about HTTP requests, responses, sessions, CLI arguments, or framework-specific request objects. They receive **plain data** and return **results**.

```
// WRONG — Action coupled to HTTP context
class CreateUserAction {
    handle(request) {
        name = request.input('name')  // ❌ Depends on HTTP
    }
}

// RIGHT — Action receives plain data
class CreateUserAction {
    handle(data) {
        name = data.name  // ✅ Context-free
    }
}
```

## 2. Naming Conventions

Use the `Action` suffix consistently across all languages, and give each Action its own file. File names should identify exactly one operation.

| Language | Class/Function Name | File Name |
|---|---|---|
| PHP | `CreateUserAction` | `CreateUserAction.php` |
| TypeScript | `CreateUserAction` (class) or `createUserAction` (function) | `create-user.action.ts` |
| Python | `CreateUserAction` (class) or `create_user_action` (function) | `create_user_action.py` |
| Go | `CreateUserAction` (struct) | `create_user_action.go` |
| C# | `CreateUserAction` | `CreateUserAction.cs` |
| Java | `CreateUserAction` | `CreateUserAction.java` |
| Kotlin | `CreateUserAction` | `CreateUserAction.kt` |
| Rust | `CreateUserAction` (struct) or `create_user_action` (function) | `create_user_action.rs` |

### Directory Structure

Organize Actions under a dedicated directory, grouped by domain directories when the project grows. Domain folders may group files; source files must not group Actions.

```
src/
└── actions/
    ├── auth/
    │   ├── register-user.action.ts
    │   └── verify-email.action.ts
    ├── billing/
    │   ├── process-payment.action.ts
    │   └── cancel-subscription.action.ts
    └── team/
        ├── create-invitation.action.ts
        └── remove-member.action.ts
```

Do not create aggregate Action implementation files such as `auth.actions.ts`, `billing-actions.ts`, `actions.py`, or `UserActions.java`. Those files hide operation boundaries and make it too easy for one Action to grow into a service.

## 3. Dependency Injection

### Classes: Constructor Injection

When Actions are classes, **dependencies go in the constructor**. The invocation method receives only the **runtime data** specific to the operation.

- **Constructor** = services, repositories, gateways, other Actions (resolved once, reusable).
- **Invocation method** = request data, entities, parameters (vary per call).

### Functions: Parameter Injection

When Actions are plain functions, **all dependencies are parameters** alongside the runtime data.

## 4. Invocable Classes

When the language supports it, prefer **invokable** (callable) classes. This makes the Action usable as if it were a function. Do **not** mark Action classes as `final` — leave them non-final for extensibility.

> **Why non-final?** Actions should remain open for extension in projects that need to decorate, wrap, or extend behavior through inheritance. The single-responsibility nature of Actions already limits misuse. Making them final adds rigidity with limited benefit.

## 5. Language-Specific Examples

### PHP

PHP Actions use `__invoke()` to make the class callable. Dependencies are injected via the constructor.

**Action:**

```php
<?php

declare(strict_types=1);

namespace App\Actions\Auth;

use App\Models\User;
use App\Services\PasswordHasher;
use App\Notifications\WelcomeNotification;

class RegisterUserAction
{
    public function __construct(
        private PasswordHasher $hasher,
        private WelcomeNotification $notification,
    ) {}

    /**
     * @param array{name: string, email: string, password: string} $data
     */
    public function __invoke(array $data): User
    {
        $user = User::create([
            'name'     => $data['name'],
            'email'    => $data['email'],
            'password' => $this->hasher->hash($data['password']),
        ]);

        $this->notification->send($user);

        return $user;
    }
}
```

**Test:**

```php
<?php

declare(strict_types=1);

namespace Tests\Actions\Auth;

use App\Actions\Auth\RegisterUserAction;
use App\Models\User;
use App\Services\PasswordHasher;
use App\Notifications\WelcomeNotification;
use PHPUnit\Framework\TestCase;

class RegisterUserActionTest extends TestCase
{
    public function test_it_registers_a_user(): void
    {
        $hasher = $this->createMock(PasswordHasher::class);
        $hasher->method('hash')->willReturn('hashed_password');

        $notification = $this->createMock(WelcomeNotification::class);
        $notification->expects($this->once())->method('send');

        $action = new RegisterUserAction($hasher, $notification);

        $user = ($action)([
            'name'     => 'Jane Doe',
            'email'    => 'jane@example.com',
            'password' => 'secret123',
        ]);

        $this->assertInstanceOf(User::class, $user);
        $this->assertSame('Jane Doe', $user->name);
        $this->assertSame('jane@example.com', $user->email);
    }
}
```

### TypeScript (Class-Based)

TypeScript Actions use a callable pattern via a dedicated method. Dependencies are injected via the constructor.

**Action:**

```typescript
// src/actions/auth/register-user.action.ts

import { UserRepository } from '../../repositories/user.repository';
import { PasswordHasher } from '../../services/password-hasher';
import { EmailService } from '../../services/email.service';
import { User } from '../../models/user';

interface RegisterUserData {
  name: string;
  email: string;
  password: string;
}

export class RegisterUserAction {
  constructor(
    private readonly userRepository: UserRepository,
    private readonly hasher: PasswordHasher,
    private readonly emailService: EmailService,
  ) {}

  async execute(data: RegisterUserData): Promise<User> {
    const hashedPassword = await this.hasher.hash(data.password);

    const user = await this.userRepository.create({
      name: data.name,
      email: data.email,
      password: hashedPassword,
    });

    await this.emailService.sendWelcome(user);

    return user;
  }
}
```

**Test:**

```typescript
// src/actions/auth/register-user.action.test.ts

import { RegisterUserAction } from './register-user.action';
import { UserRepository } from '../../repositories/user.repository';
import { PasswordHasher } from '../../services/password-hasher';
import { EmailService } from '../../services/email.service';

describe('RegisterUserAction', () => {
  it('should register a user and send welcome email', async () => {
    const mockUserRepo: jest.Mocked<UserRepository> = {
      create: jest.fn().mockResolvedValue({
        id: '1',
        name: 'Jane Doe',
        email: 'jane@example.com',
      }),
    } as any;

    const mockHasher: jest.Mocked<PasswordHasher> = {
      hash: jest.fn().mockResolvedValue('hashed_password'),
    } as any;

    const mockEmailService: jest.Mocked<EmailService> = {
      sendWelcome: jest.fn().mockResolvedValue(undefined),
    } as any;

    const action = new RegisterUserAction(
      mockUserRepo,
      mockHasher,
      mockEmailService,
    );

    const user = await action.execute({
      name: 'Jane Doe',
      email: 'jane@example.com',
      password: 'secret123',
    });

    expect(user.name).toBe('Jane Doe');
    expect(user.email).toBe('jane@example.com');
    expect(mockHasher.hash).toHaveBeenCalledWith('secret123');
    expect(mockEmailService.sendWelcome).toHaveBeenCalledWith(user);
  });
});
```

### TypeScript (Function-Based)

When class-based Actions are not needed, use a plain function. All dependencies become parameters. A function-based Action still gets its own file; never export multiple Actions from a shared `*.actions.ts` module.

**Action:**

```typescript
// src/actions/auth/register-user.action.ts

import { UserRepository } from '../../repositories/user.repository';
import { PasswordHasher } from '../../services/password-hasher';
import { EmailService } from '../../services/email.service';
import { User } from '../../models/user';

interface RegisterUserData {
  name: string;
  email: string;
  password: string;
}

export async function registerUserAction(
  userRepository: UserRepository,
  hasher: PasswordHasher,
  emailService: EmailService,
  data: RegisterUserData,
): Promise<User> {
  const hashedPassword = await hasher.hash(data.password);

  const user = await userRepository.create({
    name: data.name,
    email: data.email,
    password: hashedPassword,
  });

  await emailService.sendWelcome(user);

  return user;
}
```

**Test:**

```typescript
// src/actions/auth/register-user.action.test.ts

import { registerUserAction } from './register-user.action';

describe('registerUserAction', () => {
  it('should register a user and send welcome email', async () => {
    const mockUserRepo = {
      create: jest.fn().mockResolvedValue({
        id: '1',
        name: 'Jane Doe',
        email: 'jane@example.com',
      }),
    };

    const mockHasher = {
      hash: jest.fn().mockResolvedValue('hashed_password'),
    };

    const mockEmailService = {
      sendWelcome: jest.fn().mockResolvedValue(undefined),
    };

    const user = await registerUserAction(
      mockUserRepo as any,
      mockHasher as any,
      mockEmailService as any,
      { name: 'Jane Doe', email: 'jane@example.com', password: 'secret123' },
    );

    expect(user.name).toBe('Jane Doe');
    expect(mockEmailService.sendWelcome).toHaveBeenCalledWith(user);
  });
});
```

### Python

Python Actions use `__call__` to make instances callable. Dependencies are injected via `__init__`.

**Action:**

```python
# src/actions/auth/register_user_action.py

from dataclasses import dataclass
from models.user import User
from services.password_hasher import PasswordHasher
from services.email_service import EmailService
from repositories.user_repository import UserRepository


@dataclass
class RegisterUserData:
    name: str
    email: str
    password: str


class RegisterUserAction:
    def __init__(
        self,
        user_repository: UserRepository,
        hasher: PasswordHasher,
        email_service: EmailService,
    ) -> None:
        self._user_repository = user_repository
        self._hasher = hasher
        self._email_service = email_service

    def __call__(self, data: RegisterUserData) -> User:
        hashed_password = self._hasher.hash(data.password)

        user = self._user_repository.create(
            name=data.name,
            email=data.email,
            password=hashed_password,
        )

        self._email_service.send_welcome(user)

        return user
```

**Test:**

```python
# tests/actions/auth/test_register_user_action.py

from unittest.mock import MagicMock
from actions.auth.register_user_action import RegisterUserAction, RegisterUserData


def test_it_registers_a_user():
    mock_repo = MagicMock()
    mock_repo.create.return_value = MagicMock(
        name="Jane Doe", email="jane@example.com"
    )

    mock_hasher = MagicMock()
    mock_hasher.hash.return_value = "hashed_password"

    mock_email = MagicMock()

    action = RegisterUserAction(mock_repo, mock_hasher, mock_email)

    user = action(RegisterUserData(
        name="Jane Doe",
        email="jane@example.com",
        password="secret123",
    ))

    mock_hasher.hash.assert_called_once_with("secret123")
    mock_repo.create.assert_called_once()
    mock_email.send_welcome.assert_called_once_with(user)
```

### Go

Go Actions use a struct with a single `Execute` method. Dependencies are injected via the constructor function.

**Action:**

```go
// actions/auth/register_user_action.go

package auth

type RegisterUserData struct {
    Name     string
    Email    string
    Password string
}

type RegisterUserAction struct {
    userRepo     UserRepository
    hasher       PasswordHasher
    emailService EmailService
}

func NewRegisterUserAction(
    userRepo UserRepository,
    hasher PasswordHasher,
    emailService EmailService,
) *RegisterUserAction {
    return &RegisterUserAction{
        userRepo:     userRepo,
        hasher:       hasher,
        emailService: emailService,
    }
}

func (a *RegisterUserAction) Execute(data RegisterUserData) (*User, error) {
    hashedPassword, err := a.hasher.Hash(data.Password)
    if err != nil {
        return nil, err
    }

    user, err := a.userRepo.Create(data.Name, data.Email, hashedPassword)
    if err != nil {
        return nil, err
    }

    if err := a.emailService.SendWelcome(user); err != nil {
        return nil, err
    }

    return user, nil
}
```

**Test:**

```go
// actions/auth/register_user_action_test.go

package auth

import "testing"

func TestRegisterUserAction_Execute(t *testing.T) {
    mockRepo := &MockUserRepository{
        CreateFn: func(name, email, password string) (*User, error) {
            return &User{Name: name, Email: email}, nil
        },
    }
    mockHasher := &MockPasswordHasher{
        HashFn: func(password string) (string, error) {
            return "hashed_password", nil
        },
    }
    mockEmail := &MockEmailService{}

    action := NewRegisterUserAction(mockRepo, mockHasher, mockEmail)

    user, err := action.Execute(RegisterUserData{
        Name:     "Jane Doe",
        Email:    "jane@example.com",
        Password: "secret123",
    })

    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }
    if user.Name != "Jane Doe" {
        t.Errorf("expected name 'Jane Doe', got '%s'", user.Name)
    }
    if !mockEmail.WelcomeSent {
        t.Error("expected welcome email to be sent")
    }
}
```

### C\#

C# Actions use a class with an `Execute` method. Dependencies are injected via the constructor.

**Action:**

```csharp
// Actions/Auth/RegisterUserAction.cs

namespace App.Actions.Auth;

public class RegisterUserAction
{
    private readonly IUserRepository _userRepository;
    private readonly IPasswordHasher _hasher;
    private readonly IEmailService _emailService;

    public RegisterUserAction(
        IUserRepository userRepository,
        IPasswordHasher hasher,
        IEmailService emailService)
    {
        _userRepository = userRepository;
        _hasher = hasher;
        _emailService = emailService;
    }

    public async Task<User> Execute(RegisterUserData data)
    {
        var hashedPassword = _hasher.Hash(data.Password);

        var user = await _userRepository.CreateAsync(
            data.Name, data.Email, hashedPassword);

        await _emailService.SendWelcomeAsync(user);

        return user;
    }
}
```

**Test:**

```csharp
// Tests/Actions/Auth/RegisterUserActionTest.cs

using Moq;
using Xunit;

namespace App.Tests.Actions.Auth;

public class RegisterUserActionTest
{
    [Fact]
    public async Task Execute_RegistersUserAndSendsWelcome()
    {
        var mockRepo = new Mock<IUserRepository>();
        mockRepo.Setup(r => r.CreateAsync(It.IsAny<string>(), It.IsAny<string>(), It.IsAny<string>()))
                .ReturnsAsync(new User { Name = "Jane Doe", Email = "jane@example.com" });

        var mockHasher = new Mock<IPasswordHasher>();
        mockHasher.Setup(h => h.Hash(It.IsAny<string>())).Returns("hashed_password");

        var mockEmail = new Mock<IEmailService>();

        var action = new RegisterUserAction(mockRepo.Object, mockHasher.Object, mockEmail.Object);

        var user = await action.Execute(new RegisterUserData("Jane Doe", "jane@example.com", "secret123"));

        Assert.Equal("Jane Doe", user.Name);
        mockEmail.Verify(e => e.SendWelcomeAsync(It.IsAny<User>()), Times.Once);
    }
}
```

### Java

Java Actions use a class with an `execute` method. Dependencies are injected via the constructor.

**Action:**

```java
// src/main/java/com/app/actions/auth/RegisterUserAction.java

package com.app.actions.auth;

public class RegisterUserAction {

    private final UserRepository userRepository;
    private final PasswordHasher hasher;
    private final EmailService emailService;

    public RegisterUserAction(
            UserRepository userRepository,
            PasswordHasher hasher,
            EmailService emailService) {
        this.userRepository = userRepository;
        this.hasher = hasher;
        this.emailService = emailService;
    }

    public User execute(RegisterUserData data) {
        String hashedPassword = hasher.hash(data.password());

        User user = userRepository.create(
            data.name(), data.email(), hashedPassword);

        emailService.sendWelcome(user);

        return user;
    }
}
```

**Test:**

```java
// src/test/java/com/app/actions/auth/RegisterUserActionTest.java

package com.app.actions.auth;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class RegisterUserActionTest {

    @Test
    void execute_registersUserAndSendsWelcome() {
        var mockRepo = mock(UserRepository.class);
        var mockHasher = mock(PasswordHasher.class);
        var mockEmail = mock(EmailService.class);

        when(mockHasher.hash("secret123")).thenReturn("hashed_password");
        when(mockRepo.create("Jane Doe", "jane@example.com", "hashed_password"))
            .thenReturn(new User("Jane Doe", "jane@example.com"));

        var action = new RegisterUserAction(mockRepo, mockHasher, mockEmail);

        var user = action.execute(
            new RegisterUserData("Jane Doe", "jane@example.com", "secret123"));

        assertEquals("Jane Doe", user.name());
        verify(mockEmail).sendWelcome(user);
    }
}
```

### Kotlin

Kotlin Actions use `operator fun invoke()` to make the class callable. Dependencies are injected via the constructor.

**Action:**

```kotlin
// src/main/kotlin/com/app/actions/auth/RegisterUserAction.kt

package com.app.actions.auth

class RegisterUserAction(
    private val userRepository: UserRepository,
    private val hasher: PasswordHasher,
    private val emailService: EmailService,
) {
    operator fun invoke(data: RegisterUserData): User {
        val hashedPassword = hasher.hash(data.password)

        val user = userRepository.create(
            name = data.name,
            email = data.email,
            password = hashedPassword,
        )

        emailService.sendWelcome(user)

        return user
    }
}
```

**Test:**

```kotlin
// src/test/kotlin/com/app/actions/auth/RegisterUserActionTest.kt

package com.app.actions.auth

import io.mockk.*
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test

class RegisterUserActionTest {

    @Test
    fun `it registers a user and sends welcome email`() {
        val mockRepo = mockk<UserRepository>()
        val mockHasher = mockk<PasswordHasher>()
        val mockEmail = mockk<EmailService>(relaxed = true)

        every { mockHasher.hash("secret123") } returns "hashed_password"
        every { mockRepo.create("Jane Doe", "jane@example.com", "hashed_password") } returns
            User(name = "Jane Doe", email = "jane@example.com")

        val action = RegisterUserAction(mockRepo, mockHasher, mockEmail)

        val user = action(RegisterUserData("Jane Doe", "jane@example.com", "secret123"))

        assertEquals("Jane Doe", user.name)
        verify { mockEmail.sendWelcome(user) }
    }
}
```

### Rust

Rust Actions use a struct with an `execute` method. Dependencies are injected via the constructor.

**Action:**

```rust
// src/actions/auth/register_user_action.rs

pub struct RegisterUserAction {
    user_repository: Box<dyn UserRepository>,
    hasher: Box<dyn PasswordHasher>,
    email_service: Box<dyn EmailService>,
}

impl RegisterUserAction {
    pub fn new(
        user_repository: Box<dyn UserRepository>,
        hasher: Box<dyn PasswordHasher>,
        email_service: Box<dyn EmailService>,
    ) -> Self {
        Self { user_repository, hasher, email_service }
    }

    pub fn execute(&self, data: RegisterUserData) -> Result<User, ActionError> {
        let hashed_password = self.hasher.hash(&data.password)?;

        let user = self.user_repository.create(
            &data.name, &data.email, &hashed_password,
        )?;

        self.email_service.send_welcome(&user)?;

        Ok(user)
    }
}
```

**Test:**

```rust
// src/actions/auth/register_user_action_test.rs

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_execute_registers_user_and_sends_welcome() {
        let mock_repo = MockUserRepository::new();
        let mock_hasher = MockPasswordHasher::new("hashed_password");
        let mock_email = MockEmailService::new();

        let action = RegisterUserAction::new(
            Box::new(mock_repo),
            Box::new(mock_hasher),
            Box::new(mock_email),
        );

        let result = action.execute(RegisterUserData {
            name: "Jane Doe".to_string(),
            email: "jane@example.com".to_string(),
            password: "secret123".to_string(),
        });

        assert!(result.is_ok());
        let user = result.unwrap();
        assert_eq!(user.name, "Jane Doe");
        assert_eq!(user.email, "jane@example.com");
    }
}
```

## 6. Invocation Method Names

The method name for invoking the Action depends on the language's conventions and capabilities:

| Language | Method | Reason |
|---|---|---|
| PHP | `__invoke()` | Magic method makes the object callable: `$action($data)` |
| Python | `__call__()` | Dunder method makes the object callable: `action(data)` |
| Kotlin | `operator fun invoke()` | Operator overload makes the object callable: `action(data)` |
| TypeScript | `execute()` | No native invoke mechanism; explicit method preferred |
| Go | `Execute()` | No operator overloading; explicit method preferred |
| C# | `Execute()` | Explicit method preferred for clarity |
| Java | `execute()` | No operator overloading; explicit method preferred |
| Rust | `execute()` | No operator overloading; explicit method preferred |

> **Rule of thumb:** If the language supports making a class instance callable (invokable), use the native mechanism. Otherwise, use `execute()`.

## 7. Composing Actions

Actions can depend on other Actions to build complex workflows. Inject the dependent Action via the constructor, just like any other dependency.

```php
class CreateTeamAction
{
    public function __construct(
        private RegisterUserAction $registerUser,
        private SendInvitationAction $sendInvitation,
    ) {}

    public function __invoke(array $teamData, array $ownerData): Team
    {
        $owner = ($this->registerUser)($ownerData);

        $team = Team::create([
            'name'     => $teamData['name'],
            'owner_id' => $owner->id,
        ]);

        foreach ($teamData['invitees'] as $email) {
            ($this->sendInvitation)(['team_id' => $team->id, 'email' => $email]);
        }

        return $team;
    }
}
```

> **Important:** When an Action coordinates multiple operations that must succeed or fail together, wrap them in a transaction (database transaction, saga, or equivalent for your platform).

## 8. Testing Requirements

**Every Action must have an associated test.** When creating or modifying an Action, always create or modify the corresponding test.

### Test Naming Convention

| Language | Action File | Test File |
|---|---|---|
| PHP | `CreateUserAction.php` | `CreateUserActionTest.php` |
| TypeScript | `create-user.action.ts` | `create-user.action.test.ts` |
| Python | `create_user_action.py` | `test_create_user_action.py` |
| Go | `create_user_action.go` | `create_user_action_test.go` |
| C# | `CreateUserAction.cs` | `CreateUserActionTest.cs` |
| Java | `CreateUserAction.java` | `CreateUserActionTest.java` |
| Kotlin | `CreateUserAction.kt` | `CreateUserActionTest.kt` |
| Rust | `create_user_action.rs` | `mod tests` block inside the file, or `create_user_action_test.rs` |

### What to Test

1. **Happy path:** The Action produces the correct result with valid inputs.
2. **Side effects:** Expected side effects occur (emails sent, events dispatched, records created).
3. **Error handling:** The Action fails gracefully with invalid inputs or dependency failures.
4. **Dependencies are called correctly:** Mocked dependencies receive the expected arguments.

### Testing Strategy

- **Mock dependencies** injected via the constructor — this is why constructor injection exists.
- **Test the Action directly** — do not test through HTTP, CLI, or any framework-specific layer.
- **Use the simplest assertion** that verifies the behavior.

## 9. When NOT to Use an Action

Not every piece of code needs an Action. Do not use this pattern when:

- The operation is **trivial** (a simple CRUD store with no side effects).
- The code is **infrastructure** (HTTP client wrappers, file system utilities, string formatters).
- The logic is a **pure data transformation** with no dependencies — a simple function is better.
- The operation is a **query** with no side effects — use a dedicated query/repository pattern instead.

**Use an Action when:**

- The operation involves **business rules** (validation logic, coordination of multiple services).
- The same logic is called from **multiple entry points** (controller, CLI, job, event handler).
- The operation has **side effects** (sends emails, dispatches events, writes to external systems).
- The logic is **complex enough to deserve its own test**.

## 10. Decision Checklist

When writing or reviewing code, follow this checklist:

1. **Is this business logic?** If not, make it a library/utility.
2. **Does it do one thing?** If it does two things, split into two Actions.
3. **Is it context-free?** No HTTP requests, no CLI arguments, no session data inside the Action.
4. **Is it in its own file?** One source file defines one Action. Split grouped Actions before calling the work complete.
5. **Are dependencies in the constructor?** Services and repositories go in the constructor; runtime data goes in the invocation method.
6. **Does it use the `Action` suffix?** `CreateUserAction`, not `CreateUser` or `UserCreator`.
7. **Is it invokable?** If the language supports callable classes, use the native mechanism.
8. **Is it non-final?** Leave the class open for extension.
9. **Does a test exist?** Every Action has a corresponding test. Creating an Action without a test is incomplete work.
10. **Does the test mock dependencies?** Test the Action in isolation, not through the framework.
11. **Does it return a result?** Let the caller decide what to do with the output.

> **Every non-trivial business operation deserves a clear home. Every Action is tested. Every Action is independent.**

## 11. Validation And Completion

The skill has been applied successfully when:

- The operation is correctly classified as an Action-worthy business use case, or the agent clearly explains why an Action is not appropriate.
- The Action has one responsibility, its own source file, an `Action` suffix, plain runtime inputs, explicit dependencies, and a clear result or error behavior.
- No file defines more than one Action. Grouped Action modules such as `user.actions.ts`, `actions.py`, or `UserActions.java` are split before completion.
- Framework-specific request, response, session, route, CLI, queue, or UI objects stay outside the Action.
- The entry point that calls the Action is thin and contains only request parsing, authorization glue, response formatting, or framework integration.
- A direct Action test exists or was updated, covers the happy path and important failures or side effects, and mocks injected dependencies.
- Relevant repository checks pass, such as unit tests, type checks, linters, or framework-specific test commands.

When reviewing rather than editing, report whether each of these checks passes and identify the smallest changes needed to reach compliance.

## 12. Failure And Escalation Behavior

Do not guess when the missing information changes business behavior. Ask the user for clarification when you cannot determine:

- The exact operation boundary or whether multiple use cases are being combined.
- Required side effects, transaction behavior, authorization rules, or event/notification semantics.
- Whether the project wants the Action pattern instead of an existing service, command, handler, interactor, or CQRS convention.
- The expected error contract or return type.

If the request is clearly not Action-worthy, do not force the pattern. Use the repository's existing utility, query, repository, or infrastructure convention and explain the boundary briefly.

## 13. Output Expectations

When finishing a task with this skill, summarize:

- The Action created, updated, or intentionally avoided.
- The operation boundary and why it is one use case.
- The source file that owns the Action, especially when grouped Actions were split.
- The dependencies injected and the plain runtime input shape.
- The tests or checks run, including any that could not be run.
- Any caller changes made to keep entry points thin.

## Reference Documentation

This skill is based on the Action pattern as described in the software engineering community. No external reference files are required at this time.

### Sources

- [The Action Pattern Explained (Video)](https://youtu.be/sW8tN8cf2bE)
- [Understanding the Action Pattern — A Cleaner Way to Organize Your Code](https://medium.com/@harryespant/understanding-the-action-pattern-in-laravel-a-cleaner-way-to-organize-your-code-3c7f04666c23)
- [Action Pattern — Concept, Benefits, Best Practices](https://nabilhassen.com/action-pattern-in-laravel-concept-benefits-best-practices)
- [Action Pattern — Why I Stopped Using Fat Controllers](https://www.moisis.dev/articles/action-pattern-in-laravel)

## Scripts and Assets

- `assets/behavior-fixtures.json` - behavior fixtures for Action-pattern activation, non-activation, and validation guidance.
- `scripts/validate-fixtures.js` - validates that this skill and its behavior fixtures cover required Action-pattern boundaries.

## License information

This skill is licensed under the [MIT License](../../LICENSE).
