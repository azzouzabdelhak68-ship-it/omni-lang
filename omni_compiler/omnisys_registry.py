"""OMNISYS module registry (v6).

The single source of truth the compiler uses to resolve `import OMNISYS[.module]`
and to enforce the effect system across the OMNISYS standard library.

Each module records:
  - js_file: the JS implementation file (repo-relative) that is inlined by the
    JS emitter when the module is imported.
  - js_deps: OMNISYS modules that must be inlined first (dependency order).
  - functions: symbol -> {"type": signature, "effects": declared capabilities}.
    `effects["uses"]` is the capability vocabulary the checker enforces
    (network, filesystem, database, camera, microphone, GPU, process, secrets,
    dom, panic). `panic` marks functions that may abort control flow (throw):
    they are NOT pure and must be declared (`uses panic`) at every boundary.

Additional declarative memory effects (Pillar 2, for WASM/embedded targets):
  - allocates: function may allocate memory
  - mutates_heap: function may mutate heap memory

These are purely declarative (not auto-detected) and do not conflict with any
existing OMNISYS capability names.

Design rule (spec §17.3, "Do Not Wrap — Design Native"): the registry describes
portable semantic APIs, never host-library shapes.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OmnisysFunction:
    """A single OMNISYS standard-library function."""

    type: str
    effects: frozenset[str] = frozenset()


@dataclass(frozen=True)
class OmnisysModule:
    """One OMNISYS module (a top-level namespace under `omnisys`)."""

    js_file: str
    functions: dict[str, OmnisysFunction] = field(default_factory=dict)
    js_deps: tuple[str, ...] = ()


def _fn(type_: str, *effects: str) -> OmnisysFunction:
    return OmnisysFunction(type=type_, effects=frozenset(effects))


def _module(
    _name: str,
    js_file: str,
    deps: tuple[str, ...] = (),
    **fns: OmnisysFunction,
) -> OmnisysModule:
    return OmnisysModule(js_file=js_file, functions=dict(fns), js_deps=deps)


def _pure(type_: str) -> OmnisysFunction:
    return _fn(type_)


OMNISYS_MODULES: dict[str, OmnisysModule] = {
    'core': _module(
        'core',
        'omnisys/core.js',
        option=_pure('fn(any) -> Option'),
        some=_pure('fn(any) -> Option'),
        none=_pure('fn() -> Option'),
        is_some=_pure('fn(Option) -> Boolean'),
        is_none=_pure('fn(Option) -> Boolean'),
        ok=_pure('fn(any) -> Result'),
        err=_pure('fn(any) -> Result'),
        is_ok=_pure('fn(Result) -> Boolean'),
        is_err=_pure('fn(Result) -> Boolean'),
        identity=_pure('fn(any) -> any'),
        type_of=_pure('fn(any) -> Text'),
        panic=_fn('fn(Text) -> None', 'panic'),
        abs=_pure('fn(Number) -> Number'),
        min=_pure('fn(Number, Number) -> Number'),
        max=_pure('fn(Number, Number) -> Number'),
        clamp=_pure('fn(Number, Number, Number) -> Number'),
        round=_pure('fn(Number) -> Number'),
        floor=_pure('fn(Number) -> Number'),
        ceil=_pure('fn(Number) -> Number'),
        sqrt=_pure('fn(Number) -> Number'),
        length=_pure('fn(any) -> Number'),
        is_empty=_pure('fn(any) -> Boolean'),
        split=_pure('fn(Text, Text) -> List'),
        char_at=_pure('fn(Text, Number) -> Text'),
        substring=_pure('fn(Text, Number, Number) -> Text'),
        to_number=_pure('fn(Text) -> Number'),
    ),
    'collections': _module(
        'collections',
        'omnisys/collections.js',
        ('core',),
        list_push=_pure('fn(List, any) -> List'),
        list_pop=_pure('fn(List) -> any'),
        list_get=_pure('fn(List, Number) -> any'),
        list_set=_pure('fn(List, Number, any) -> List'),
        list_slice=_pure('fn(List, Number, Number) -> List'),
        list_append=_pure('fn(List, List) -> List'),
        list_contains=_pure('fn(List, any) -> Boolean'),
        list_index_of=_pure('fn(List, any) -> Number'),
        list_remove=_pure('fn(List, Number) -> List'),
        list_sort=_pure('fn(List) -> List'),
        list_reverse=_pure('fn(List) -> List'),
        list_fold=_pure('fn(List, fn, any) -> any'),
        list_map=_pure('fn(List, fn) -> List'),
        list_filter=_pure('fn(List, fn) -> List'),
        list_join=_pure('fn(List, Text) -> Text'),
        list_zip=_pure('fn(List, List) -> List'),
        map_get=_pure('fn(Map, any) -> any'),
        map_set=_pure('fn(Map, any, any) -> Map'),
        map_remove=_pure('fn(Map, any) -> Map'),
        map_has=_pure('fn(Map, any) -> Boolean'),
        map_keys=_pure('fn(Map) -> List'),
        map_values=_pure('fn(Map) -> List'),
        map_size=_pure('fn(Map) -> Number'),
        set_add=_pure('fn(Set, any) -> Set'),
        set_remove=_pure('fn(Set, any) -> Set'),
        set_has=_pure('fn(Set, any) -> Boolean'),
        set_size=_pure('fn(Set) -> Number'),
        set_union=_pure('fn(Set, Set) -> Set'),
        set_intersection=_pure('fn(Set, Set) -> Set'),
        set_difference=_pure('fn(Set, Set) -> Set'),
        deque_push_front=_pure('fn(Deque, any) -> Deque'),
        deque_push_back=_pure('fn(Deque, any) -> Deque'),
        deque_pop_front=_pure('fn(Deque) -> any'),
        deque_pop_back=_pure('fn(Deque) -> any'),
        deque_size=_pure('fn(Deque) -> Number'),
        heap_push=_pure('fn(Heap, any) -> Heap'),
        heap_pop=_pure('fn(Heap) -> any'),
        heap_peek=_pure('fn(Heap) -> any'),
        heap_size=_pure('fn(Heap) -> Number'),
        ring_new=_pure('fn(Number) -> RingBuffer'),
        ring_push=_pure('fn(RingBuffer, any) -> RingBuffer'),
        ring_pop=_pure('fn(RingBuffer) -> any'),
        ring_size=_pure('fn(RingBuffer) -> Number'),
    ),
    'error': _module(
        'error',
        'omnisys/error.js',
        ('core',),
        error=_pure('fn(Text) -> Error'),
        error_code=_pure('fn(Text, Text) -> Error'),
        error_message=_pure('fn(Error) -> Text'),
        error_code_of=_pure('fn(Error) -> Text'),
        error_stack=_pure('fn(Error) -> Text'),
        error_with_context=_pure('fn(Error, Text, any) -> Error'),
        error_has_context=_pure('fn(Error, Text) -> Boolean'),
        error_to_dict=_pure('fn(Error) -> Map'),
        throw_error=_fn('fn(Error) -> None', 'panic'),
        is_error=_pure('fn(any) -> Boolean'),
    ),
    'serde': _module(
        'serde',
        'omnisys/serde.js',
        ('core',),
        json_encode=_pure('fn(any) -> Text'),
        json_decode=_fn('fn(Text) -> any', 'panic'),
        csv_encode=_pure('fn(List) -> Text'),
        csv_decode=_pure('fn(Text) -> List'),
        to_hex=_pure('fn(Text) -> Text'),
        from_hex=_pure('fn(Text) -> Text'),
        base64_encode=_pure('fn(Text) -> Text'),
        base64_decode=_fn('fn(Text) -> Text', 'panic'),
        schema_validate=_pure('fn(any, Map) -> Boolean'),
    ),
    'async': _module(
        'async',
        'omnisys/async.js',
        ('core',),
        task=_pure('fn(fn) -> Task'),
        delay=_pure('fn(Number) -> Task'),
        interval=_pure('fn(Number, fn() -> None) -> Task'),
        timeout=_pure('fn(Number, fn() -> None) -> Task'),
        tick=_pure('fn(fn() -> None) -> Task'),
        cancel=_pure('fn(Task) -> None'),
        **{'await': _pure('fn(Task) -> Any')},
        all=_pure('fn(List) -> Task'),
        race=_pure('fn(List) -> Task'),
        any=_pure('fn(List) -> Task'),
        channel=_pure('fn(Number) -> Channel'),
        channel_send=_pure('fn(Channel, any) -> Task'),
        channel_recv=_pure('fn(Channel) -> Task'),
        is_promise=_pure('fn(any) -> Boolean'),
    ),
    'fs': _module(
        'fs',
        'omnisys/fs.js',
        ('core',),
        read_file=_fn('fn(Text) -> Text', 'filesystem'),
        write_file=_fn('fn(Text, Text) -> Text', 'filesystem'),
        append_file=_fn('fn(Text, Text) -> Text', 'filesystem'),
        delete_file=_fn('fn(Text) -> Boolean', 'filesystem'),
        file_exists=_fn('fn(Text) -> Boolean', 'filesystem'),
        file_size=_fn('fn(Text) -> Number', 'filesystem'),
        list_dir=_fn('fn(Text) -> List', 'filesystem'),
        make_dir=_fn('fn(Text) -> Boolean', 'filesystem'),
        remove_dir=_fn('fn(Text) -> Boolean', 'filesystem'),
        rename_file=_fn('fn(Text, Text) -> Boolean', 'filesystem'),
        copy_file=_fn('fn(Text, Text) -> Boolean', 'filesystem'),
        join_path=_pure('fn(Text, Text) -> Text'),
        basename=_pure('fn(Text) -> Text'),
        dirname=_pure('fn(Text) -> Text'),
    ),
    'test': _module(
        'test',
        'omnisys/test.js',
        ('core', 'collections'),
        assert_true=_pure('fn(Boolean, Text) -> None'),
        assert_eq=_pure('fn(any, any) -> None'),
        assert_throws=_pure('fn(fn) -> Boolean'),
        property=_pure('fn(fn, Number) -> Boolean'),
        bench=_pure('fn(fn, Number) -> Number'),
        fail=_pure('fn(Text) -> None'),
    ),
    'ui': _module(
        'ui',
        'omnisys/ui.js',
        ('core', 'collections'),
        element=_pure('fn(Text, Map, List) -> Element'),
        text=_pure('fn(Text) -> Element'),
        button=_pure('fn(Text, fn) -> Element'),
        row=_pure('fn(List) -> Element'),
        column=_pure('fn(List) -> Element'),
        input=_pure('fn(Text, Text) -> Element'),
        render=_pure('fn(Element) -> Text'),
        to_html=_pure('fn(Element) -> Text'),
        bind=_pure('fn(Element, Text, any) -> Element'),
        state=_pure('fn(any) -> State'),
        state_get=_pure('fn(State) -> any'),
        state_set=_pure('fn(State, any) -> State'),
        state_on_change=_pure('fn(State, fn) -> None'),
        get_value=_fn('fn(Text) -> Text', 'dom'),
        get_form_data=_fn('fn(Text) -> Map', 'dom'),
    ),
    'db': _module(
        'db',
        'omnisys/db.js',
        ('core', 'collections'),
        create_db=_fn('fn(Text) -> Database', 'database'),
        create_table=_fn('fn(Database, Text, Map) -> Table', 'database'),
        insert=_fn('fn(Table, Map) -> Map', 'database'),
        select=_fn('fn(Table, fn) -> List', 'database'),
        update=_fn('fn(Table, fn, Map) -> Number', 'database'),
        delete=_fn('fn(Table, fn) -> Number', 'database'),
        count=_fn('fn(Table, fn) -> Number', 'database'),
        drop_table=_fn('fn(Database, Text) -> Boolean', 'database'),
        schema=_fn('fn(Table) -> Map', 'database'),
        table_size=_fn('fn(Table) -> Number', 'database'),
        db_open=_fn('fn(Text) -> None', 'database', 'filesystem'),
        db_query=_fn('fn(Text, List) -> List', 'database'),
        db_exec=_fn('fn(Text, List) -> Number', 'database'),
        db_close=_fn('fn() -> None', 'database'),
    ),
    'net': _module(
        'net',
        'omnisys/net.js',
        ('core', 'collections'),
        server=_fn('fn(fn) -> Server', 'network'),
        start=_fn('fn(Server) -> Server', 'network'),
        request=_fn('fn(Server, Text, Text, Text) -> Response', 'network'),
        get=_fn('fn(Server, Text) -> Response', 'network'),
        post=_fn('fn(Server, Text, Text) -> Response', 'network'),
        middleware=_fn('fn(fn, List) -> fn', 'network'),
        response=_pure('fn(Number, Text) -> Response'),
        response_json=_pure('fn(Number, any) -> Response'),
        status_of=_pure('fn(Response) -> Number'),
        body_of=_pure('fn(Response) -> Text'),
    ),
    'http': _module(
        'http',
        'omnisys/http.js',
        ('core', 'net'),
        client=_fn('fn() -> Client', 'network'),
        send=_fn('fn(Client, Text, Text, Text, Number) -> Response', 'network'),
        get=_fn('fn(Text, Number) -> Response', 'network'),
        post=_fn('fn(Text, Text, Number) -> Response', 'network'),
        put=_fn('fn(Text, Text, Number) -> Response', 'network'),
        delete=_fn('fn(Text, Number) -> Response', 'network'),
        json_get=_fn('fn(Text, Number) -> any', 'network'),
        json_post=_fn('fn(Text, any, Number) -> any', 'network'),
        redirect=_pure('fn(Text, Number) -> Response'),
        not_found=_pure('fn(Text) -> Response'),
    ),
    'graphics': _module(
        'graphics',
        'omnisys/graphics.js',
        ('core',),
        canvas=_pure('fn(Number, Number) -> Canvas'),
        clear=_pure('fn(Canvas, Text) -> Canvas'),
        line=_pure('fn(Canvas, Number, Number, Number, Number, Text) -> Canvas'),
        rect=_pure('fn(Canvas, Number, Number, Number, Number, Text) -> Canvas'),
        circle=_pure('fn(Canvas, Number, Number, Number, Text) -> Canvas'),
        polygon=_pure('fn(Canvas, List, Text) -> Canvas'),
        text=_pure('fn(Canvas, Text, Number, Number, Text) -> Canvas'),
        fill=_pure('fn(Canvas, Text) -> Canvas'),
        stroke=_pure('fn(Canvas, Text) -> Canvas'),
        render=_pure('fn(Canvas) -> List'),
        to_json=_pure('fn(Canvas) -> Map'),
    ),
    'gpu': _module(
        'gpu',
        'omnisys/gpu.js',
        ('core', 'graphics'),
        buffer=_fn('fn(List) -> Buffer', 'GPU'),
        compute=_fn('fn(fn, List, Number) -> List', 'GPU'),
        parallel=_fn('fn(fn, List) -> List', 'GPU'),
        add=_fn('fn(List, List) -> List', 'GPU'),
        scale=_fn('fn(List, Number) -> List', 'GPU'),
        dot=_fn('fn(List, List) -> Number', 'GPU'),
        matmul=_fn('fn(List, List) -> List', 'GPU'),
        normalize=_fn('fn(List) -> List', 'GPU'),
        device_info=_fn('fn() -> Map', 'GPU'),
    ),
    'scene': _module(
        'scene',
        'omnisys/scene.js',
        ('core',),
        new_scene=_pure('fn() -> Scene'),
        node=_pure('fn(Scene, Text) -> Node'),
        mesh=_pure('fn(Scene, Text, Text) -> Node'),
        camera=_pure('fn(Scene, Text) -> Node'),
        light=_pure('fn(Scene, Text, Text) -> Node'),
        add=_pure('fn(Scene, Text, Text) -> Scene'),
        transform=_pure('fn(Scene, Text, Map) -> Scene'),
        remove=_pure('fn(Scene, Text) -> Scene'),
        snapshot=_pure('fn(Scene) -> Map'),
        update=_pure('fn(Scene, Number) -> Scene'),
        to_json=_pure('fn(Scene) -> Map'),
    ),
    'sim': _module(
        'sim',
        'omnisys/sim.js',
        ('core', 'collections'),
        world=_pure('fn() -> World'),
        entity=_pure('fn(World, Text) -> Entity'),
        component=_pure('fn(World, Text, Text, any) -> World'),
        get=_pure('fn(World, Text, Text) -> any'),
        system=_pure('fn(World, fn) -> World'),
        run=_pure('fn(World, Number) -> World'),
        query=_pure('fn(World, Text) -> List'),
        remove_entity=_pure('fn(World, Text) -> World'),
        snapshot=_pure('fn(World) -> Map'),
        entities=_pure('fn(World) -> List'),
    ),
    'audio': _module(
        'audio',
        'omnisys/audio.js',
        ('core',),
        buffer=_pure('fn(Number) -> AudioBuffer'),
        tone=_pure('fn(Number, Number, Number) -> AudioBuffer'),
        silence=_pure('fn(Number, Number) -> AudioBuffer'),
        sample=_pure('fn(AudioBuffer, Number) -> Number'),
        mix=_pure('fn(AudioBuffer, AudioBuffer) -> AudioBuffer'),
        append=_pure('fn(AudioBuffer, AudioBuffer) -> AudioBuffer'),
        gain=_pure('fn(AudioBuffer, Number) -> AudioBuffer'),
        encode_wav=_pure('fn(AudioBuffer) -> Text'),
        duration=_pure('fn(AudioBuffer) -> Number'),
        length=_pure('fn(AudioBuffer) -> Number'),
    ),
    'video': _module(
        'video',
        'omnisys/video.js',
        ('core', 'audio'),
        frame=_pure('fn(Number, Number) -> VideoFrame'),
        frame_from_ascii=_pure('fn(List) -> VideoFrame'),
        set_pixel=_pure('fn(VideoFrame, Number, Number, Text) -> VideoFrame'),
        timeline=_pure('fn(Number) -> Timeline'),
        add_frame=_pure('fn(Timeline, VideoFrame) -> Timeline'),
        seek=_pure('fn(Timeline, Number) -> VideoFrame'),
        frame_count=_pure('fn(Timeline) -> Number'),
        fps_of=_pure('fn(Timeline) -> Number'),
        metadata=_pure('fn(Timeline) -> Map'),
    ),
    'platform': _module(
        'platform',
        'omnisys/platform.js',
        ('core',),
        info=_fn('fn() -> Map', 'process'),
        os=_fn('fn() -> Text', 'process'),
        arch=_fn('fn() -> Text', 'process'),
        env=_fn('fn(Text) -> Text', 'process'),
        now=_pure('fn() -> Number'),
        sleep_ms=_fn('fn(Number) -> Number', 'process'),
        capabilities=_pure('fn() -> List'),
    ),
    'crypto': _module(
        'crypto',
        'omnisys/crypto.js',
        ('core', 'error'),
        sha256=_pure('fn(Text) -> Text'),
        sha1=_pure('fn(Text) -> Text'),
        hmac=_pure('fn(Text, Text) -> Text'),
        to_hex=_pure('fn(Text) -> Text'),
        from_hex=_pure('fn(Text) -> Text'),
        random_bytes=_fn('fn(Number) -> Text', 'secrets'),
        encrypt_aes=_fn('fn(Text, Text) -> Map', 'secrets'),
        decrypt_aes=_fn('fn(Map, Text) -> Text', 'secrets'),
        kdf=_fn('fn(Text, Text, Number) -> Text', 'secrets'),
        constant_time_eq=_pure('fn(Text, Text) -> Boolean'),
    ),
    'auth': _module(
        'auth',
        'omnisys/auth.js',
        ('core', 'crypto'),
        token=_fn('fn(Text, Map, Text) -> Text', 'secrets'),
        verify_token=_fn('fn(Text, Text) -> Map', 'secrets'),
        token_subject=_fn('fn(Text) -> Text', 'secrets'),
        hash_password=_fn('fn(Text, Text) -> Text', 'secrets'),
        verify_password=_fn('fn(Text, Text) -> Boolean', 'secrets'),
        session_new=_fn('fn(Text, Text, Number) -> Map', 'secrets'),
        session_valid=_fn('fn(Map) -> Boolean', 'secrets'),
    ),
    'observability': _module(
        'observability',
        'omnisys/observability.js',
        ('core', 'collections'),
        log=_pure('fn(Text, Text, Map) -> None'),
        info=_pure('fn(Text, Map) -> None'),
        warn=_pure('fn(Text, Map) -> None'),
        error=_pure('fn(Text, Map) -> None'),
        metric=_pure('fn(Text, Number) -> None'),
        metric_value=_pure('fn(Text) -> Number'),
        trace_begin=_pure('fn(Text) -> Number'),
        trace_end=_pure('fn(Number, Map) -> None'),
        snapshot=_pure('fn() -> Map'),
        clear=_pure('fn() -> None'),
        profile=_pure('fn(fn, Number) -> Number'),
    ),
    'tool': _module(
        'tool',
        'omnisys/tool.js',
        ('core',),
        tokenize=_pure('fn(Text) -> List'),
        check=_fn('fn(Text) -> Map', 'process'),
        explain=_fn('fn(Text) -> Map', 'process'),
        line_count=_pure('fn(Text) -> Number'),
        identifier_count=_pure('fn(Text) -> Number'),
    ),
    'ai': _module(
        'ai',
        'omnisys/ai.js',
        ('core',),
        tensor=_pure('fn(List, List) -> Tensor'),
        tensor_zeros=_pure('fn(List) -> Tensor'),
        tensor_ones=_pure('fn(List) -> Tensor'),
        tensor_shape=_pure('fn(Tensor) -> List'),
        tensor_add=_pure('fn(Tensor, Tensor) -> Tensor'),
        tensor_scale=_pure('fn(Tensor, Number) -> Tensor'),
        tensor_matmul=_pure('fn(Tensor, Tensor) -> Tensor'),
        tensor_relu=_pure('fn(Tensor) -> Tensor'),
        tensor_sigmoid=_pure('fn(Tensor) -> Tensor'),
        tensor_sum=_pure('fn(Tensor) -> Number'),
        tensor_to_json=_pure('fn(Tensor) -> Map'),
        tensor_from_json=_pure('fn(Map) -> Tensor'),
        linear=_pure('fn(List, List, List) -> List'),
        softmax=_pure('fn(List) -> List'),
        predict=_pure('fn(List, List) -> List'),
    ),
    'pkg': _module(
        'pkg',
        'omnisys/pkg.js',
        ('core', 'serde', 'fs'),
        manifest=_fn('fn(Text) -> Map', 'filesystem'),
        create=_pure('fn(Text, Text, Map) -> Map'),
        resolve=_pure('fn(Text, Text, Map) -> List'),
        install=_fn('fn(Text, Map) -> Map', 'filesystem'),
        registry_add=_pure('fn(Map, Text, Map) -> Map'),
        registry_get=_pure('fn(Map, Text, Text) -> Map'),
        list_dependencies=_pure('fn(Map) -> List'),
        parse_version=_pure('fn(Text) -> Map'),
        satisfies=_pure('fn(Text, Text) -> Boolean'),
        resolve_versions=_pure('fn(List, Map, Map) -> Map'),
        compute_checksum=_pure('fn(Text) -> Text'),
    ),
}


ROOT_NAMESPACES = ('omnisys', 'OMNISYS')


def resolve_import(path: tuple[str, ...]) -> OmnisysModule | None:
    """Resolve an `import` path to an OMNISYS module (or None when invalid)."""
    if not path:
        return None
    if path[0] != 'OMNISYS':
        return None
    if len(path) == 1:
        return OMNISYS_MODULES['core']
    if len(path) == 2:  # noqa: PLR2004
        return OMNISYS_MODULES.get(path[1])
    return None


def is_omnisys_call(name: str) -> bool:
    """Return True when `name` is a dotted OMNISYS call (`omnisys.<module>.<fn>`)."""
    for root in ROOT_NAMESPACES:
        if name.startswith(root + '.'):
            parts = name.split('.')
            return (
                len(parts) == 3  # noqa: PLR2004
                and parts[1] in OMNISYS_MODULES
                and parts[2] in OMNISYS_MODULES[parts[1]].functions
            )
    return False


def omnisys_effects(name: str) -> set[str]:
    """Return the declared capability effects for an OMNISYS call name."""
    if not is_omnisys_call(name):
        return set()
    _, module_name, fn_name = name.split('.')
    fn = OMNISYS_MODULES[module_name].functions[fn_name]
    return set(fn.effects)


def js_files_for(imports: list[list[str]]) -> list[str]:
    """Return repo-relative JS implementation files for the imported modules.

    Files are returned in dependency order (deps first, deduplicated).
    """
    wanted: dict[str, OmnisysModule] = {}
    for path in imports:
        resolved = resolve_import(tuple(path))
        if resolved is None:
            continue
        _collect_deps(resolved, wanted)
    ordered: list[str] = []
    seen: set[str] = set()
    for module_name in sorted(wanted):
        module = wanted[module_name]
        for dep_name in module.js_deps:
            dep = OMNISYS_MODULES[dep_name]
            if dep.js_file not in seen:
                seen.add(dep.js_file)
                ordered.append(dep.js_file)
        if module.js_file not in seen:
            seen.add(module.js_file)
            ordered.append(module.js_file)
    return ordered


def _collect_deps(module: OmnisysModule, into: dict[str, OmnisysModule]) -> None:
    for dep_name in module.js_deps:
        dep = OMNISYS_MODULES[dep_name]
        if dep_name not in into:
            _collect_deps(dep, into)
            into[dep_name] = dep
    into[module_name_of(module.js_file)] = module


def module_name_of(js_file: str) -> str:
    """Return the OMNISYS module name for a repo-relative JS implementation file."""
    return js_file.rsplit('/', 1)[-1].removesuffix('.js')


def module_names() -> list[str]:
    """Return the sorted OMNISYS module names."""
    return sorted(OMNISYS_MODULES)
