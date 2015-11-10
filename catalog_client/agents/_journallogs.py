from os import environ

from twisted.internet.utils import getProcessValue, getProcessOutput
from twisted.internet.defer import DeferredList

from eliot import Message

_HOST_COMMAND = [
    b"/usr/sbin/chroot", b"/host",
]

def _check(unit):
    command = _HOST_COMMAND + [b"/usr/bin/systemctl", b"status"] + [unit]
    Message.new(
        system="log-agent:os-detection:journald",
        unit=unit,
        command=command,
    ).write()
    return getProcessValue(command[0], command[1:], env=environ)

class _JournaldCollector(object):
    mark = None

    _units = [
        b"flocker-container-agent",
        b"flocker-dataset-agent",
        b"flocker-control",
    ]

    def detect(self):
        checking = _check(b"flocker-dataset-agent")

        def succeed_or_fail(result):
            Message.new(
                system="log-agent:os-detection:journald",
                result=result,
            ).write()
            if result == 0:
                return True
            return False

        def succeed_or_check_control(result):
            Message.new(
                system="log-agent:os-detection:journald",
                result=result,
            ).write()
            if result == 0:
                return True
            return _check(b"flocker-control").addCallback(succeed_or_fail)

        checking.addCallback(succeed_or_check_control)

        return checking

    def collect(self):
        reading_journals = DeferredList(list(
            self._read_journal(unit)
            for unit in self.units
        ))

        def check_results(read_results, units):
            combined_results = {}
            for (unit, (success, result)) in zip(units, read_results):
                if success:
                    journal, cursor = result
                    combined_results[unit] = journal
                    self.cursors[unit] = cursor
            return combined_results

        reading_journals.addCallback(check_results, self.units)
        return reading_journals

    def _read_journal(self, unit):
        def read_journal(unit, cursor):
            command = _HOST_COMMAND + [
                b"/usr/bin/journalctl", b"--output", b"cat", b"--unit", unit,
                b"--show-cursor",
            ]
            if cursor is None:
                command.extend([b"--lines", b"0"])
            else:
                command.extend([b"--after-cursor", cursor])

            return getProcessOutput(command[0], command[1:], env=environ)

        reading = read_journal()

        def split_cursor(journal):
            # -- cursor: s=91bc(...)0984
            lines = journal.splitlines()
            cursor_line = lines.pop()
            if cursor_line.startswith("-- cursor: "):
                cursor = cursor_line[len("-- cursor: "):].strip()
            else:
                Message.new(
                    system="log-agent:journald-collector:cursor-missing",
                    cursor_line=cursor_line,
                ).write()
                cursor = None
            return (lines, cursor)
        saving = reading.addCallback(split_cursor)

        def format_results(lines):
            return dict(lines=lines)
        saving.addCallback(format_results)
        return saving
