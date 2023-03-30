"""Filter for download"""

import re
from datetime import datetime
from typing import Any, Optional

from ply import lex, yacc

from utils.format import get_byte_from_str
from utils.meta_data import MetaData, NoneObj, ReString


# pylint: disable = R0904
class BaseFilter:
    """for normal filter"""

    def __init__(self, debug: bool = False):
        """
         Parameters
        ----------
        debug: bool
            If output debug info

        """
        self.names: dict = {}
        self.debug = debug
        # Build the lexer and parser
        # lex.lex(module=self)
        self.lexer = lex.lex(module=self)
        self.yacc = yacc.yacc(module=self)

    def reset(self):
        """Reset all symbol"""
        self.names.clear()

    def exec(self, filter_str: str) -> Any:
        """Exec filter str"""
        # )  #
        # return yacc.parse(filter_str, debug=self.debug)
        return self.yacc.parse(filter_str, debug=self.debug)

    def _output(self, output_str: str):
        """For print debug info"""
        if self.debug:
            print(output_str)

    reserved = {
        "and": "AND",
        "or": "OR",
    }

    tokens = (
        "NAME",
        "NUMBER",
        "GE",
        "LE",
        "LOR",
        "LAND",
        "STRING",
        "RESTRING",
        "BYTE",
        "EQ",
        "NE",
        "TIME",
        "AND",
        "OR",
    )

    literals = ["=", "+", "-", "*", "/", "(", ")", ">", "<"]

    # t_NAME = r'[a-zA-Z_][a-zA-Z0-9_]*'
    t_GE = r">="
    t_LE = r"<="
    t_LOR = r"\|\|"
    t_LAND = r"&&"
    t_EQ = r"=="
    t_NE = r"!="

    def t_BYTE(self, t):
        r"\d{1,}(B|KB|MB|GB|TB)"
        t.value = get_byte_from_str(t.value)
        t.type = "NUMBER"
        return t

    def t_TIME(self, t):
        r"\d{4}-\d{1,2}-\d{1,2}[ ]{1,}\d{1,2}:\d{1,2}:\d{1,2}"
        t.value = datetime.strptime(t.value, "%Y-%m-%d %H:%M:%S")
        return t

    def t_STRING(self, t):
        r"'.*?'"
        # r"'([^\\']+|\\'|\\\\)*'"
        t.value = t.value[1:-1]
        return t

    def t_RESTRING(self, t):
        r"r'.*?'"
        # r"r'([^\\']+|\\'|\\\\)*'"
        t.value = t.value[2:-1]
        return t

    def t_NAME(self, t):
        r"[a-zA-Z_][a-zA-Z0-9_]*"
        t.type = BaseFilter.reserved.get(t.value, "NAME")
        return t

    def t_NUMBER(self, t):
        r"\d+"
        t.value = int(t.value)
        return t

    t_ignore = " \t"

    def t_newline(self, t):
        r"\n+"
        t.lexer.lineno += t.value.count("\n")

    def t_error(self, t):
        """print error"""
        print(f"Illegal character '{t.value[0]}'")
        t.lexer.skip(1)

    precedence = (
        ("left", "LOR", "OR"),
        ("left", "LAND", "AND"),
        ("left", "EQ", "NE"),
        ("nonassoc", ">", "<", "GE", "LE"),
        ("left", "+", "-"),
        ("left", "*", "/"),
        ("right", "UMINUS"),
    )

    def p_statement_assign(self, p):
        'statement : NAME "=" expression'
        return self.p_expression_eq(p)
        # self.names[p[1]] = p[3]

    def p_statement_expr(self, p):
        "statement : expression"
        self._output(p[1])
        p[0] = p[1]

    def p_expression_binop(self, p):
        """expression : expression '+' expression
        | expression '-' expression
        | expression '*' expression
        | expression '/' expression"""
        self.check_type(p)
        if isinstance(p[1], NoneObj):
            p[1] = 0
        if isinstance(p[3], NoneObj):
            p[3] = 0

        if p[2] == "+":
            p[0] = p[1] + p[3]
        elif p[2] == "-":
            p[0] = p[1] - p[3]
        elif p[2] == "*":
            p[0] = p[1] * p[3]
        elif p[2] == "/":
            p[0] = p[1] / p[3]

        self._output(f"binop {p[1]} {p[2]} {p[3]} = {p[0]}")

    def p_expression_comp(self, p):
        """expression : expression '>' expression
        | expression '<' expression"""
        self.check_type(p)
        if isinstance(p[1], NoneObj) or isinstance(p[3], NoneObj):
            p[0] = True
            return

        if p[1] is None or p[3] is None:
            p[0] = True
            return
        if p[2] == ">":
            p[0] = p[1] > p[3]
        elif p[2] == "<":
            p[0] = p[1] < p[3]

    def p_expression_uminus(self, p):
        "expression : '-' expression %prec UMINUS"
        p[0] = -p[2]

    def p_expression_ge(self, p):
        "expression : expression GE expression"
        self.check_type(p)
        if isinstance(p[1], NoneObj) or isinstance(p[3], NoneObj):
            p[0] = True
            return

        if p[1] is None or p[3] is None:
            p[0] = True
            return

        p[0] = p[1] >= p[3]
        self._output(f"{p[1]} {p[2]} {p[3]} {p[0]}")

    def p_expression_le(self, p):
        "expression : expression LE expression"
        self.check_type(p)
        if isinstance(p[1], NoneObj) or isinstance(p[3], NoneObj):
            p[0] = True
            return

        if p[1] is None or p[3] is None:
            p[0] = True
            return

        p[0] = p[1] <= p[3]
        self._output(f"{p[1]} {p[2]} {p[3]} = {p[0]}")

    def p_expression_eq(self, p):
        "expression : expression EQ expression"
        self.check_type(p)
        if isinstance(p[1], NoneObj) or isinstance(p[3], NoneObj):
            p[0] = True
            return

        if p[1] is None or p[3] is None:
            p[0] = True
            return

        if isinstance(p[3], ReString):
            if not isinstance(p[1], str):
                p[0] = 0
                return
            p[0] = re.fullmatch(p[3].re_string, p[1], re.MULTILINE) is not None
            self._output(f"{p[1]} {p[2]} {p[3].re_string} {p[0]}")
        elif isinstance(p[1], ReString):
            if not isinstance(p[3], str):
                p[0] = 0
                return
            p[0] = re.fullmatch(p[1].re_string, p[3], re.MULTILINE) is not None
            self._output(f"{p[1]} {p[2]} {p[3].re_string} {p[0]}")
        else:
            p[0] = p[1] == p[3]
            self._output(f"{p[1]} {p[2]} {p[3]} {p[0]}")

    def p_expression_ne(self, p):
        "expression : expression NE expression"
        self.check_type(p)
        if isinstance(p[1], NoneObj) or isinstance(p[3], NoneObj):
            p[0] = True
            return

        if p[1] is None or p[3] is None:
            p[0] = True
            return
        if isinstance(p[3], ReString):
            if not isinstance(p[1], str):
                p[0] = 0
                return
            p[0] = re.fullmatch(p[3].re_string, p[1], re.MULTILINE) is None
            self._output(f"{p[1]} {p[2]} {p[3].re_string} {p[0]}")
        elif isinstance(p[1], ReString):
            if not isinstance(p[3], str):
                p[0] = 0
                return
            p[0] = re.fullmatch(p[1].re_string, p[3], re.MULTILINE) is None
            self._output(f"{p[1]} {p[2]} {p[3].re_string} {p[0]}")
        else:
            p[0] = p[1] != p[3]
            self._output(f"{p[1]} {p[2]} {p[3]} = {p[0]}")

    def p_expression_group(self, p):
        "expression : '(' expression ')'"
        p[0] = p[2]

    def p_expression_number(self, p):
        "expression : NUMBER"
        p[0] = p[1]

    def p_expression_time(self, p):
        "expression : TIME"
        p[0] = p[1]

    def p_expression_name(self, p):
        "expression : NAME"
        try:
            p[0] = self.names[p[1]]
        except Exception as e:
            self._output(f"Undefined name '{p[1]}'")
            raise ValueError(f"Undefined name {p[1]}") from e
            # FIXME: not support not exist name
            # p[0] = NoneObj()

    def p_expression_lor(self, p):
        "expression : expression LOR expression"
        p[0] = p[1] or p[3]

    def p_expression_land(self, p):
        "expression : expression LAND expression"
        p[0] = p[1] and p[3]

    def p_expression_or(self, p):
        "expression : expression OR expression"
        p[0] = p[1] or p[3]

    def p_expression_and(self, p):
        "expression : expression AND expression"
        p[0] = p[1] and p[3]

    def p_expression_string(self, p):
        "expression : STRING"
        p[0] = p[1]

    def p_expression_restring(self, p):
        "expression : RESTRING"
        p[0] = ReString(p[1])
        self._output("RESTRING : " + p[0].re_string)

    # pylint: disable = C0116
    def p_error(self, p):
        if p:
            raise ValueError(f"Syntax error at '{p.value}'")

        raise ValueError("Syntax error at EOF")

    def check_type(self, p):
        """Check filter type if is right"""
        if p[1] is None or p[1] is NoneObj or p[3] is None or p[3] is NoneObj:
            return
        if isinstance(p[1], str):
            if not isinstance(p[3], str) and not isinstance(p[3], ReString):
                raise ValueError(f"{p[1]} is str but {p[3]} is not")
        elif isinstance(p[1], int):
            if not isinstance(p[3], int):
                raise ValueError(f"{p[1]} is int but {p[3]} is not")
        elif isinstance(p[1], bool):
            if not isinstance(p[3], bool):
                raise ValueError(f"{p[1]} is bool but {p[3]} is not")
        elif isinstance(p[1], datetime):
            if not isinstance(p[3], datetime):
                raise ValueError(f"{p[1]} is datetime but {p[3]} is not")


class Filter:
    """filter for telegram download"""

    def __init__(self):
        self.filter = BaseFilter()

    def set_meta_data(self, meta_data: MetaData):
        """Set meta data for filter"""
        self.filter.reset()
        self.filter.names = meta_data.data()

    def set_debug(self, debug: bool):
        """Set Filter Debug Model"""
        self.filter.debug = debug

    def exec(self, filter_str: str) -> bool:
        """Exec filter str"""

        if self.filter.names:
            res = self.filter.exec(filter_str)
            if isinstance(res, bool):
                return res
            return False
        raise ValueError("meta data cannot be empty!")

    def check_filter(self, filter_str: str) -> tuple[bool, Optional[str]]:
        """check filter str"""
        try:
            return not self.exec(filter_str) is None, None
        except Exception as e:
            return False, str(e)
