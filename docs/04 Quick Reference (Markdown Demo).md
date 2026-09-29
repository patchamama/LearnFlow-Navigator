# Quick Reference (Markdown Demo)

This chapter is written in **plain Markdown**, not HTML — the reader converts it on the fly and syntax-highlights any fenced code block. It follows your system's light/dark setting automatically, same as the rest of this course.

Everything below is here to show the feature off: headers, lists, `inline code`, blockquotes, links, and highlighted code blocks in several languages.

## Python

```python
def greet(name):
    # a friendly default
    return f"Hello, {name}!"

print(greet("Ada"))
```

## JSON

```json
{"name": "Ada", "age": 36, "active": true, "score": 3.14}
```

## XML

```xml
<person id="1" active="true">
  <!-- a comment -->
  <name>Ada Lovelace</name>
</person>
```

## HTML

```html
<button class="btn" onclick="alert('hi')">Click me</button>
```

## Java

```java
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello from Java");
    }
}
```

## Go

```go
package main

import "fmt"

func main() {
    fmt.Println("Hello from Go")
}
```

## PHP

```php
function greet($name) {
    // a friendly default
    return "Hello, {$name}!";
}
```

## Why this matters

- Drop a `.md` file anywhere a `.html` chapter could go — root folder or inside a numbered module — and it becomes a chapter automatically.
- Numbering and titles work exactly like exported HTML chapters (`04 Quick Reference (Markdown Demo).md` → "Quick Reference (Markdown Demo)").
- No backend is required to render this: it happens entirely in your browser.

> **Tip**: this is also how the [live demo](https://patchamama.github.io/LearnFlow-Navigator/) itself demonstrates the feature — this exact file is one of its chapters.
