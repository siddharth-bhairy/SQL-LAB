import re

reserved_words = {
    "add", "all", "allocate", "alter", "and", "any", "are", "as", "asensitive",
    "assertion", "asymmetric", "at", "atomic", "authorization", "avg", "begin",
    "between", "bigint", "binary", "blob", "boolean", "both", "by", "call",
    "called", "cascaded", "case", "cast", "char", "character", "check", "clob",
    "close", "collate", "column", "commit", "condition", "connect", "constraint",
    "continue", "corresponding", "create", "cross", "cube", "current", "current_date",
    "current_path", "current_role", "current_time", "current_timestamp", "current_user",
    "cursor", "cycle", "data", "date", "day", "deallocate", "dec", "decimal",
    "declare", "default", "delete", "deref", "describe", "deterministic", "disconnect",
    "distinct", "do", "double", "drop", "dynamic", "each", "element", "else",
    "elseif", "end", "escape", "except", "exec", "execute", "exists", "exit",
    "external", "false", "fetch", "filter", "float", "for", "foreign", "free",
    "from", "full", "function", "get", "global", "grant", "group", "grouping",
    "handler", "having", "hold", "hour", "identity", "if", "immediate", "in",
    "indicator", "inner", "inout", "input", "insensitive", "insert", "int",
    "integer", "intersect", "interval", "into", "is", "iterate", "join", "key",
    "language", "large", "lateral", "leading", "leave", "left", "level", "like",
    "local", "localtime", "localtimestamp", "loop", "lower", "match", "max",
    "member", "merge", "method", "min", "minute", "modifies", "module", "month",
    "multiset", "names", "national", "natural", "nchar", "nclob", "new", "next",
    "no", "none", "not", "null", "numeric", "of", "old", "on", "only", "open",
    "option", "or", "order", "out", "outer", "output", "over", "overlaps",
    "parameter", "partition", "precision", "prepare", "primary", "procedure",
    "range", "reads", "real", "recursive", "ref", "references", "referencing",
    "release", "repeat", "resignal", "result", "return", "returns", "revoke",
    "right", "rollback", "rollup", "row", "rows", "savepoint", "scope", "scroll",
    "search", "second", "select", "sensitive", "session_user", "set", "signal",
    "similar", "smallint", "some", "specific", "specifictype", "sql", "sqlexception",
    "sqlstate", "sqlwarning", "start", "static", "submultiset", "symmetric",
    "system", "system_user", "table", "tablesample", "then", "time", "timestamp",
    "timezone_hour", "timezone_minute", "to", "trailing", "translation", "treat",
    "trigger", "true", "undo", "union", "unique", "unknown", "unnest", "until",
    "update", "upper", "user", "using", "value", "values", "varchar", "varying",
    "when", "whenever", "where", "while", "window", "with", "within", "without",
    "year"
}

data_types = {
    "int", "integer", "smallint", "bigint", "numeric", "decimal", "dec",
    "float", "real", "double", "char", "character", "varchar", "clob",
    "nchar", "nclob", "date", "time", "timestamp", "interval", "boolean",
    "binary", "varbinary", "blob", "xml", "json", "text", "tinyint",
    "mediumint", "bit", "money", "serial"
}

# Valid comparison operators for WHERE / SET clauses
OPERATORS = {'=', '>', '<', '>=', '<=', '!=', '<>', 'like', 'in', 'is', 'between', 'not'}

# Column-level constraint keyword tokens — used as a quick membership reference.
# The actual multi-token parsing (NOT NULL, PRIMARY KEY, REFERENCES, etc.)
# is handled token-by-token inside _parse_column_def.
COLUMN_CONSTRAINTS = {"not", "null", "primary", "unique", "default",
                      "auto_increment", "check", "references", "constraint"}


# ── helpers ──────────────────────────────────────────────────────────────────

def _check_parens(query):
    """Return an error string if parentheses are unbalanced, else None."""
    if query.count('(') != query.count(')'):
        return "Unbalanced parentheses."
    return None


def _parse_type(raw_type):
    """
    Split a raw type token like 'varchar(255)' into
    {'name': 'varchar', 'length': '255'} or {'name': 'int', 'length': None}.
    """
    m = re.match(r'^(\w+)\(([^)]+)\)$', raw_type)
    if m:
        return {"name": m.group(1).lower(), "length": m.group(2)}
    return {"name": raw_type.lower(), "length": None}


def _parse_where_conditions(where_clause):
    """
    Parse a WHERE clause into a list of condition dicts.
    Handles: col OP val, col IS NULL, col IS NOT NULL, col BETWEEN a AND b.
    Returns (conditions_list, errors_list).
    """
    conditions = []
    errors = []

    # Temporarily mask BETWEEN…AND so its inner AND is not treated as a splitter.
    # We mask the entire "col BETWEEN x AND y" fragment as a single token.
    between_slots = {}
    def _mask_between(m):
        key = f"__BTW{len(between_slots)}__"
        between_slots[key] = m.group(0)
        return key

    masked = re.sub(
        r'\w+\s+BETWEEN\s+\S+\s+AND\s+\S+',
        _mask_between,
        where_clause,
        flags=re.IGNORECASE
    )

    raw_conds = re.split(r'\b(?:and|or)\b', masked, flags=re.IGNORECASE)
    # Restore masked BETWEEN expressions
    restored = []
    for c in raw_conds:
        c = c.strip()
        restored.append(between_slots.get(c, c))
    for raw in restored:
        cond = raw.strip()
        if not cond:
            continue

        tokens = cond.split()
        col_name = tokens[0].lower()

        if col_name in reserved_words:
            errors.append(f"Column name in WHERE cannot be a reserved word: '{col_name}'")

        # IS NULL / IS NOT NULL  (2 or 3 tokens, no value needed)
        if len(tokens) >= 2 and tokens[1].lower() == "is":
            rest = " ".join(t.lower() for t in tokens[2:])
            if rest not in ("null", "not null"):
                errors.append(f"Invalid IS expression in WHERE: '{cond}'")
            else:
                conditions.append({
                    "column": col_name,
                    "operator": "IS",
                    "value": rest.upper()
                })
            continue

        # BETWEEN … AND … (5 tokens: col BETWEEN val1 AND val2)
        if len(tokens) >= 2 and tokens[1].lower() == "between":
            if len(tokens) != 5 or tokens[3].lower() != "and":
                errors.append(f"Invalid BETWEEN expression in WHERE: '{cond}'")
            else:
                conditions.append({
                    "column": col_name,
                    "operator": "BETWEEN",
                    "value": [tokens[2], tokens[4]]
                })
            continue

        # Standard:  col OP value
        if len(tokens) < 3:
            errors.append(f"Incomplete WHERE condition: '{cond}'")
            continue

        operator = tokens[1].lower()
        value = " ".join(tokens[2:])

        if operator not in OPERATORS:
            errors.append(f"Invalid operator in WHERE clause: '{operator}'")

        conditions.append({
            "column": col_name,
            "operator": operator,
            "value": value
        })

    return conditions, errors



def _parse_column_def(col_def):
    """
    Parse a single column definition string into a dict.
    Returns (col_dict, errors_list).

    col_dict keys:
      name        – column name (str)
      type        – data type   (str)
      length      – type length/precision if present, else None (str | None)
      constraints – list of recognised constraint strings, e.g. ["NOT NULL", "PRIMARY KEY"]
      default     – default value if DEFAULT clause present, else None (str | None)
      references  – {"table": ..., "column": ...} if REFERENCES clause present, else None
    """
    errors = []
    parts = col_def.split()

    if len(parts) < 2:
        return None, [f"Invalid column definition (need at least name + type): '{col_def}'"]

    col_name = parts[0].lower()
    type_info = _parse_type(parts[1])
    data_type = type_info["name"]

    if col_name in reserved_words:
        errors.append(f"Column name cannot be a reserved word: '{col_name}'")

    if data_type not in data_types:
        errors.append(f"Invalid or unsupported data type: '{parts[1]}'")

    constraints = []
    default_value = None
    references = None

    i = 2
    while i < len(parts):
        token = parts[i].lower()

        # ── NOT NULL ──────────────────────────────────────────────────────────
        if token == "not" and i + 1 < len(parts) and parts[i + 1].lower() == "null":
            constraints.append("NOT NULL")
            i += 2

        # ── NULL ──────────────────────────────────────────────────────────────
        elif token == "null":
            constraints.append("NULL")
            i += 1

        # ── PRIMARY KEY ───────────────────────────────────────────────────────
        elif token == "primary" and i + 1 < len(parts) and parts[i + 1].lower() == "key":
            constraints.append("PRIMARY KEY")
            i += 2

        # ── UNIQUE ────────────────────────────────────────────────────────────
        elif token == "unique":
            constraints.append("UNIQUE")
            i += 1

        # ── AUTO_INCREMENT ────────────────────────────────────────────────────
        elif token == "auto_increment":
            constraints.append("AUTO_INCREMENT")
            i += 1

        # ── DEFAULT <value> ───────────────────────────────────────────────────
        elif token == "default":
            if i + 1 < len(parts):
                default_value = parts[i + 1]
                i += 2
            else:
                errors.append(f"DEFAULT keyword in column '{col_name}' has no value.")
                i += 1

        # ── REFERENCES <table> or REFERENCES <table>(<col>) ──────────────────
        elif token == "references":
            if i + 1 >= len(parts):
                errors.append(
                    f"REFERENCES in column '{col_name}' is missing the target table name."
                )
                i += 1
                continue

            ref_token = parts[i + 1]   # e.g. "orders(id)"  or  "orders"
            i += 2

            # Case 1: table and column combined — "orders(id)"
            combined = re.match(r'^(\w+)\((\w+)\)$', ref_token)
            if combined:
                ref_table = combined.group(1).lower()
                ref_col   = combined.group(2).lower()

            # Case 2: table only on this token, column in next token — "orders" "(" "id" ")"
            # or "orders" "(id)"  — handle the space-split variants
            else:
                ref_table = ref_token.removesuffix("(").lower()

                # Collect the parenthesised column name which may be split across tokens
                # e.g. parts = [..., "orders", "(id)"]  or  [..., "orders", "(", "id", ")"]
                ref_col = None
                if i < len(parts) and parts[i].startswith("("):
                    bracket_token = parts[i].strip("()")
                    if bracket_token:                       # "(id)"
                        ref_col = bracket_token.lower()
                        i += 1
                    else:                                   # "(" alone
                        if i + 1 < len(parts):
                            ref_col = parts[i + 1].strip(")").lower()
                            i += 2
                        else:
                            errors.append(
                                f"REFERENCES in column '{col_name}': "
                                f"malformed column reference after '{ref_table}'."
                            )

            # Validate the referenced table / column names
            if ref_table in reserved_words:
                errors.append(
                    f"REFERENCES target table cannot be a reserved word: '{ref_table}'"
                )
            if ref_col and ref_col in reserved_words:
                errors.append(
                    f"REFERENCES target column cannot be a reserved word: '{ref_col}'"
                )
            if ref_table and not re.match(r'^\w+$', ref_table):
                errors.append(
                    f"REFERENCES target table is not a valid identifier: '{ref_table}'"
                )
            if ref_col and not re.match(r'^\w+$', ref_col):
                errors.append(
                    f"REFERENCES target column is not a valid identifier: '{ref_col}'"
                )

            references = {"table": ref_table, "column": ref_col}

        # ── CHECK / CONSTRAINT — skip the rest of the token (not deeply parsed) ──
        elif token in ("check", "constraint"):
            # Consume everything remaining; table-level checks are stripped upstream
            i = len(parts)

        # ── Unknown token ─────────────────────────────────────────────────────
        else:
            # Don't error — could be an unrecognised but harmless keyword
            i += 1

    col_dict = {
        "name": col_name,
        "type": data_type,
        "length": type_info["length"],
        "constraints": constraints,
        "default": default_value,
        "references": references
    }
    return col_dict, errors


# ── CREATE ───────────────────────────────────────────────────────────────────

def create_validator(query):
    errors = []
    create_regex = re.compile(
        r"^\s*create\s+table\s+(?P<table>\w+)\s*\((?P<body>.+)\)\s*;?\s*$",
        re.IGNORECASE | re.DOTALL
    )

    ans = re.match(create_regex, query.strip())
    if not ans:
        return {"errors": ["Invalid CREATE TABLE syntax. "
                           "Expected: CREATE TABLE <name> (<col_def>, ...);"]}

    table = ans.group("table").strip().lower()
    body  = ans.group("body").strip()

    if table in reserved_words:
        errors.append(f"Table name cannot be a reserved word: '{table}'")

    # Split on commas NOT inside parentheses
    raw_columns = re.split(r',\s*(?![^()]*\))', body)

    parsed_columns = []
    for col_def in raw_columns:
        col_def = col_def.strip()
        if not col_def:
            continue

        # Skip table-level constraints (PRIMARY KEY (...), UNIQUE (...), etc.)
        if re.match(r'^(primary\s+key|unique|check|constraint|foreign\s+key|index)\b',
                    col_def, re.IGNORECASE):
            continue

        col_dict, col_errors = _parse_column_def(col_def)
        errors.extend(col_errors)
        if col_dict:
            parsed_columns.append(col_dict)

    if errors:
        return {"errors": errors}

    return {
        "type": "create",
        "tableName": table,
        "columns": parsed_columns
    }


# ── UPDATE ───────────────────────────────────────────────────────────────────

def update_validator(query):
    errors = []
    query = query.rstrip(";").strip()

    paren_err = _check_parens(query)
    if paren_err:
        errors.append(paren_err)

    update_pattern = re.compile(
        r"^\s*update\s+(?P<table>\w+)\s+set\s+(?P<set_clause>(?:(?!\bwhere\b).)+?)(?:\s+where\s+(?P<where>.+))?$",
        re.IGNORECASE | re.DOTALL
    )

    ans = re.match(update_pattern, query)
    if not ans:
        return {"errors": ["Invalid UPDATE syntax. "
                           "Expected: UPDATE <table> SET <col=val> [WHERE <cond>]"]}

    table      = ans.group("table").strip().lower()
    set_clause = ans.group("set_clause").strip()
    where_raw  = ans.group("where").strip() if ans.group("where") else None

    if table in reserved_words:
        errors.append(f"Table name cannot be a reserved word: '{table}'")

    # Parse SET assignments
    parsed_assignments = []
    for item in [a.strip() for a in set_clause.split(",")]:
        if "=" not in item:
            errors.append(f"Invalid SET assignment (missing '='): '{item}'")
        else:
            col_name, _, value = item.partition("=")
            col_name = col_name.strip().lower()
            value    = value.strip()
            if col_name in reserved_words:
                errors.append(f"Column name in SET cannot be a reserved word: '{col_name}'")
            else:
                parsed_assignments.append({"column": col_name, "value": value})

    # Parse WHERE clause
    parsed_conditions = []
    if where_raw:
        parsed_conditions, where_errors = _parse_where_conditions(where_raw)
        errors.extend(where_errors)

    if errors:
        return {"errors": errors}

    result = {
        "type": "update",
        "tableName": table,
        "assignments": parsed_assignments
    }
    if parsed_conditions:
        result["where"] = parsed_conditions
    return result


# ── SELECT ───────────────────────────────────────────────────────────────────

def select_validator(query):
    errors = []
    query = query.rstrip(";").strip()

    paren_err = _check_parens(query)
    if paren_err:
        errors.append(paren_err)

    select_pattern = re.compile(
        r"^\s*select\s+(?P<cols>.+?)\s+from\s+(?P<table>\w+)"
        r"(?:\s+where\s+(?P<where>.+?))?"
        r"(?:\s+order\s+by\s+(?P<order>.+?))?"
        r"\s*$",
        re.IGNORECASE | re.DOTALL
    )

    ans = re.match(select_pattern, query)
    if not ans:
        return {"errors": ["Invalid SELECT syntax. "
                           "Expected: SELECT <cols> FROM <table> "
                           "[WHERE <cond>] [ORDER BY <col> [ASC|DESC]]"]}

    cols      = ans.group("cols").strip()
    table     = ans.group("table").strip().lower()
    where_raw = ans.group("where").strip() if ans.group("where") else None
    order_raw = ans.group("order").strip() if ans.group("order") else None

    if table in reserved_words:
        errors.append(f"Table name cannot be a reserved word: '{table}'")

    # Parse column list
    parsed_cols = []
    if cols == "*":
        parsed_cols = [{"name": "*", "alias": None}]
    else:
        for col in [c.strip() for c in cols.split(",")]:
            alias_parts = re.split(r'\s+as\s+', col, flags=re.IGNORECASE)
            col_expr  = alias_parts[0].strip().lower()
            alias     = alias_parts[1].strip() if len(alias_parts) > 1 else None
            base_name = col_expr.split('.')[-1]   # handle table.column notation

            if base_name in reserved_words:
                errors.append(f"Column name cannot be a reserved word: '{base_name}'")
            if not re.match(r'^[\w.*]+$', col_expr):
                errors.append(f"Invalid column identifier: '{col_expr}'")

            parsed_cols.append({"name": col_expr, "alias": alias})

    # Parse WHERE clause
    parsed_conditions = []
    if where_raw:
        parsed_conditions, where_errors = _parse_where_conditions(where_raw)
        errors.extend(where_errors)

    # Parse ORDER BY clause
    parsed_order = []
    if order_raw:
        for oc in re.split(r',\s*', order_raw):
            oc_parts = oc.strip().split()
            if not oc_parts:
                continue
            oc_name = oc_parts[0].lower()
            direction = "ASC"   # default

            if oc_name in reserved_words:
                errors.append(f"ORDER BY column cannot be a reserved word: '{oc_name}'")

            if len(oc_parts) == 2:
                if oc_parts[1].lower() not in ("asc", "desc"):
                    errors.append(f"Invalid ORDER BY direction: '{oc_parts[1]}' (use ASC or DESC)")
                else:
                    direction = oc_parts[1].upper()
            elif len(oc_parts) > 2:
                errors.append(f"Unexpected tokens in ORDER BY: '{oc}'")

            parsed_order.append({"column": oc_name, "direction": direction})

    if errors:
        return {"errors": errors}

    result = {
        "type": "select",
        "tableName": table,
        "columns": parsed_cols
    }
    if parsed_conditions:
        result["where"] = parsed_conditions
    if parsed_order:
        result["orderBy"] = parsed_order
    return result


# ── ALTER ────────────────────────────────────────────────────────────────────

def alter_validator(query):
    errors = []
    # Normalise "DROP COLUMN" → action='drop column', details=<col>
    pattern = re.compile(
        r"^\s*alter\s+table\s+(?P<table_name>\w+)\s+"
        r"(?P<action>add|drop\s+column|drop)\s+(?P<details>.+?)\s*;?\s*$",
        re.IGNORECASE
    )

    ans = re.match(pattern, query.strip())
    if not ans:
        return {"errors": ["Invalid ALTER TABLE syntax. "
                           "Expected: ALTER TABLE <name> ADD <col type> | DROP [COLUMN] <col>"]}

    table   = ans.group("table_name").strip().lower()
    action  = re.sub(r'\s+', ' ', ans.group("action").strip().lower())  # normalise spaces
    details = ans.group("details").strip()
    det_list = details.split()

    if table in reserved_words:
        errors.append(f"Table name cannot be a reserved word: '{table}'")

    parsed_column = None

    if action == "add":
        if len(det_list) < 2:
            errors.append("ADD requires a column name and data type.")
        else:
            col_dict, col_errors = _parse_column_def(details)
            errors.extend(col_errors)
            parsed_column = col_dict

    elif "drop" in action:          # covers "drop" and "drop column"
        if not det_list:
            errors.append("DROP requires a column name.")
        else:
            col_name = det_list[0].lower()
            if col_name in reserved_words:
                errors.append(f"Column name cannot be a reserved word: '{col_name}'")
            else:
                parsed_column = {"name": col_name}

    if errors:
        return {"errors": errors}

    result = {
        "type": "alter",
        "tableName": table,
        "action": action.replace(" ", "_").upper()   # e.g. "ADD", "DROP", "DROP_COLUMN"
    }
    if parsed_column:
        result["column"] = parsed_column
    return result


# ── DELETE ───────────────────────────────────────────────────────────────────

def delete_validator(query):
    errors = []
    query = query.strip()

    paren_err = _check_parens(query)
    if paren_err:
        errors.append(paren_err)

    delete_pattern = re.compile(
        r"^\s*delete\s+from\s+(?P<table>\w+)(?:\s+where\s+(?P<where>.+?))?;?\s*$",
        re.IGNORECASE | re.DOTALL
    )

    ans = re.match(delete_pattern, query)
    if not ans:
        return {"errors": ["Invalid DELETE syntax. "
                           "Expected: DELETE FROM <table> [WHERE <cond>]"]}

    table     = ans.group("table").strip().lower()
    where_raw = ans.group("where").strip() if ans.group("where") else None

    if table in reserved_words:
        errors.append(f"Table name cannot be a reserved word: '{table}'")

    parsed_conditions = []
    if where_raw:
        parsed_conditions, where_errors = _parse_where_conditions(where_raw)
        errors.extend(where_errors)

    if errors:
        return {"errors": errors}

    result = {
        "type": "delete",
        "tableName": table
    }
    if parsed_conditions:
        result["where"] = parsed_conditions
    return result


# ── DISPATCHER ───────────────────────────────────────────────────────────────

def query_check(query):
    """Detect SQL statement type and dispatch to the appropriate validator."""
    query = query.strip()
    if not query:
        return {"errors": ["Empty query."]}

    keyword = query.split()[0].upper()
    dispatch = {
        "SELECT": select_validator,
        "CREATE": create_validator,
        "ALTER":  alter_validator,
        "DELETE": delete_validator,
        "UPDATE": update_validator,
    }

    validator = dispatch.get(keyword)
    if validator:
        return validator(query)
    return {"errors": [f"Unsupported or unrecognised SQL statement: '{keyword}'"]}
