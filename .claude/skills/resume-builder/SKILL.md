```markdown
# resume-builder Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches the core development patterns and conventions used in the `resume-builder` Java repository. It covers file naming, import/export styles, commit message conventions, and testing patterns. While no specific frameworks or automated workflows are detected, this guide provides best practices and suggested commands for efficient development.

## Coding Conventions

### File Naming
- Use **PascalCase** for all file names.
  - Example: `ResumeBuilder.java`, `UserProfileManager.java`

### Import Style
- Use **relative imports** within the project.
  - Example:
    ```java
    import resumeBuilder.models.UserProfile;
    ```

### Export Style
- Use **named exports** (public classes or methods).
  - Example:
    ```java
    public class ResumeBuilder {
        // class implementation
    }
    ```

### Commit Messages
- Use the `feat` prefix for new features.
- Commit messages are concise (average 53 characters).
  - Example: `feat: add PDF export functionality`

## Workflows

### Add a New Feature
**Trigger:** When implementing a new feature or module  
**Command:** `/add-feature`

1. Create a new Java file using PascalCase (e.g., `NewFeature.java`).
2. Use relative imports for dependencies within the project.
3. Export your main class or methods using `public`.
4. Write a commit message starting with `feat:` followed by a brief description.
5. Run or write tests for your new feature (see Testing Patterns).

### Refactor Existing Code
**Trigger:** When improving or restructuring code without adding features  
**Command:** `/refactor`

1. Identify the code to refactor.
2. Rename files if necessary, maintaining PascalCase.
3. Update relative imports as needed.
4. Ensure all exports remain named and public.
5. Test the refactored code.
6. Commit with a clear message (e.g., `refactor: improve UserProfile validation`).

### Run Tests
**Trigger:** To verify code correctness after changes  
**Command:** `/run-tests`

1. Locate test files matching the `*.test.*` pattern.
2. Run tests using your preferred Java test runner (framework is unspecified).
3. Review test results and fix any failures.

## Testing Patterns

- Test files follow the `*.test.*` naming convention (e.g., `ResumeBuilder.test.java`).
- The specific testing framework is not detected; use standard Java testing tools such as JUnit or TestNG.
- Place test files alongside or in a dedicated test directory.

**Example Test File:**
```java
import org.junit.Test;
import static org.junit.Assert.*;

public class ResumeBuilderTest {
    @Test
    public void testBuildResume() {
        // test implementation
    }
}
```

## Commands
| Command        | Purpose                                         |
|----------------|-------------------------------------------------|
| /add-feature   | Scaffold and commit a new feature               |
| /refactor      | Refactor existing code and update as needed     |
| /run-tests     | Run all test files in the repository            |
```
