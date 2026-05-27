# Language

Shared vocabulary for every suggestion this skill makes. Use these
terms exactly — don't substitute "component," "service," "API," or
"boundary." Consistent language is the whole point.

## Terms

**Requirements** are the desired functional, non-functional and behavioral characteristics of a program or system.
  - **Functional requirements** dictate "what" a system must do and "why" it does (its core features and actions),
  - **non-functional requirements** dictate **how** a system behaves (its quality attributes and constraints), and
  - **behaviors** are the observable actions a system takes to fulfill those requirements

A **user story** is an informal, high-level description of a software
feature written from the perspective of the end-user. It focuses
on "what" a user needs and "why" it provides value, rather than
technical specifications.  There is a tight relationship between
user stories and requirements.

**Feature, Functional and Behavioral Tests** (also called **scenarios**)
derive directly from requirements, and validate that the "what",
"why", and "where" described by the requirements is correctly delivered.
A key attribute of scenarios is that they are independent from
design and implementation details.  Scenarios are expressed in the
Gherkin language using the pattern of "GIVEN some context WHEN
something happens THEN expectation"

**Software architecture** (or simply **architecture**) is the
strategic "what" and "who"—a high-level blueprint that defines a
project's overall structure, actors/modules and modules
boundaries.  The architecture of a project is driven by requirements
and validated by scenarios.

**Software design** (or **design**) is the "how"—the tactical
structure and engineering decomposition that drives low-level
implementation details, algorithms, and logic.
Developers use design patterns and best practices to construct the
modules within architectural boundaries.

**Module** (alternatively, in jBOM, **Service**)
Anything with an interface and an implementation. Deliberately scale-agnostic — applies equally to a function, class, package, or tier-spanning slice.
_Avoid_: unit, component.

**Interface** (also **API**)
Everything a caller must know to use the module correctly. Includes
the type signature, but also invariants, ordering constraints, error
modes, required configuration, and performance characteristics.
_Avoid_: API, signature (too narrow — those refer only to the type-level surface).

**Implementation**
What's inside a module — its body of code. Distinct from **Adapter**:
a thing can be a small adapter with a large implementation (a
Postgres repo) or a large adapter with a small implementation (an
in-memory fake). Reach for "adapter" when the seam is the topic;
"implementation" otherwise.

**Unit tests** validate design practices and implementation choices.  Compared to scenarios, unit tests only live as long as the design of the moment needs them.  As implementations evolve, the unit tests written for it must adapt.

**Depth**
A measure of the leverage at an interface — the amount of behaviour
a caller (or test) can exercise per unit of interface they have to
learn. A module is **deep** when a large amount of behaviour sits
behind a small interface. A module is **shallow** when the interface
is nearly as complex as the implementation.

**Seam** _(from Michael Feathers)_
A place where you can alter behaviour without editing in that place.
The *location* at which a module's interface lives. Choosing where
to put the seam is its own design decision, distinct from what goes
behind it.
_Avoid_: boundary (overloaded with DDD's bounded context).

**Adapter**
A concrete thing that satisfies an interface at a seam. Describes *role* (what slot it fills), not substance (what's inside).

**Leverage**
What callers get from depth. More capability per unit of interface they have to learn. One implementation pays back across N call sites and M tests.

**Locality** (also, **abstraction**)
What maintainers get from depth. Change, bugs, knowledge, and verification concentrate at one place rather than spreading across callers. Fix once, fixed everywhere.

## Principles

- **Depth is a property of the interface, not the implementation.** A deep module can be internally composed of small, mockable, swappable parts — they just aren't part of the interface. A module can have **internal seams** (private to its implementation, used by its own tests) as well as the **external seam** at its interface.
- **The deletion test.** Imagine deleting the module. If complexity vanishes, the module wasn't hiding anything (it was a pass-through). If complexity reappears across N callers, the module was earning its keep.
- **The interface is the test surface.** Callers and tests cross the same seam. If you want to test *past* the interface, the module is probably the wrong shape.
- **One adapter means a hypothetical seam. Two adapters means a real one.** Don't introduce a seam unless something actually varies across it.

Requirements, by their nature, evolve over time; this implies that
architecture must also change.  By intent, Architecture is constrained
to evolve in **compatible** ways through a formal decision process
using **Architectural Decision Records** (**ADRs**) that evaluate
the pros and cons of various options, and decide on one.

**Semantic Versioning** is used to record the impact of architectural
change in a version number of the form MAJOR.MINOR.MICRO.  Incompatible
changes force an increment of the MAJOR value, addition of nre
capabilities forces an increment of the MINOR value, while
non-architectural changes (bug fixes) force increments of the MICRO
value.  We use semantic git commit phrasology to trigger automatic
versioning in our git CI/CD actions.

## Relationships

- Requirements drive Scenarios
  - Requirements drive Architecture
  - Scenarios validate Requirements by way of architecture
- Architecture drives design.
  - Design drives unit tests
    - Design drives implementations
    - Unit tests validate design by way of implementations.

- A **Module** has exactly one **Interface** (the surface it presents to callers and tests).
- **Depth** is a property of a **Module**, measured against its **Interface**.
- A **Seam** is where a **Module**'s **Interface** lives.
- An **Adapter** sits at a **Seam** and satisfies the **Interface**.
- **Depth** produces **Leverage** for callers and **Locality** for maintainers.

## Rejected framings

- **Depth as ratio of implementation-lines to interface-lines** (Ousterhout): rewards padding the implementation. We use depth-as-leverage instead.
- **"Interface" as a keyword or a class's public methods**: too narrow — interface here includes every fact a caller must know.
- **"Boundary"**: overloaded with DDD's bounded context. Say **seam** or **interface**.
