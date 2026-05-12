# tests/report_generator.py
"""
Генератор отчётов о прохождении интеграционных тестов.
Форматы: console, JSON, HTML.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class TestReport:
    """Агрегатор результатов тестов."""

    def __init__(self, test_name: str, started_at: datetime):
        self.test_name = test_name
        self.started_at = started_at
        self.finished_at: Optional[datetime] = None
        self.steps: List[Dict[str, Any]] = []
        self.summary: Dict[str, Any] = {}

    def add_step(self, name: str, success: bool, duration_sec: float,
                 details: dict = None, error: str = None):
        """Добавляет результат шага теста."""
        self.steps.append({
            "name": name,
            "success": success,
            "duration_sec": round(duration_sec, 3),
            "details": details or {},
            "error": error,
            "timestamp": datetime.now().isoformat()
        })

    def finish(self, success: bool, total_duration_sec: float):
        """Завершает тест и формирует сводку."""
        self.finished_at = datetime.now()
        passed = sum(1 for s in self.steps if s["success"])
        failed = len(self.steps) - passed

        self.summary = {
            "test_name": self.test_name,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "total_duration_sec": round(total_duration_sec, 3),
            "steps_total": len(self.steps),
            "steps_passed": passed,
            "steps_failed": failed,
            "overall_success": success and failed == 0,
            "success_rate": round(passed / len(self.steps) * 100, 1) if self.steps else 100.0
        }

    def to_json(self) -> str:
        """Экспорт в JSON."""
        return json.dumps({
            "summary": self.summary,
            "steps": self.steps
        }, indent=2, ensure_ascii=False)

    def to_console(self) -> str:
        """Форматированный вывод в консоль."""
        lines = [
            "\n" + "=" * 70,
            f"📊 ОТЧЁТ: {self.test_name}",
            "=" * 70,
            f"🕐 Старт: {self.started_at.strftime('%H:%M:%S')}",
            f"🏁 Финиш: {self.finished_at.strftime('%H:%M:%S') if self.finished_at else '...'}",
            f"⏱ Длительность: {self.summary.get('total_duration_sec', 0):.2f} сек",
            f"✅ Успешно: {self.summary.get('steps_passed', 0)}/{self.summary.get('steps_total', 0)} шагов",
            f"📈 Процент успеха: {self.summary.get('success_rate', 0):.1f}%",
            "-" * 70,
        ]

        for step in self.steps:
            icon = "✅" if step["success"] else "❌"
            duration = f"{step['duration_sec']:.3f}с"
            lines.append(f"{icon} {step['name']:40s} [{duration}]")
            if step.get("error"):
                lines.append(f"   └─ Ошибка: {step['error'][:100]}")
            if step.get("details"):
                for k, v in list(step["details"].items())[:3]:  # Показываем первые 3 детали
                    lines.append(f"   └─ {k}: {v}")

        lines.append("=" * 70)
        overall = "🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ" if self.summary.get("overall_success") else "💥 ЕСТЬ СБОИ"
        lines.append(f"ИТОГ: {overall}")
        lines.append("=" * 70 + "\n")

        return "\n".join(lines)

    def to_html(self) -> str:
        """Генерация HTML-отчёта."""
        status_color = "green" if self.summary.get("overall_success") else "red"

        rows = ""
        for step in self.steps:
            row_class = "pass" if step["success"] else "fail"
            error_html = f"<br><small class='error'>⚠️ {step['error']}</small>" if step.get("error") else ""
            details_html = "".join(
                f"<br><small>{k}: <b>{v}</b></small>"
                for k, v in list(step.get("details", {}).items())[:5]
            )
            rows += f"""
            <tr class="{row_class}">
                <td>{step['name']}</td>
                <td>{step['duration_sec']:.3f}с</td>
                <td>{'✅' if step['success'] else '❌'}</td>
                <td>{details_html} {error_html}</td>
            </tr>"""

        return f"""
<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>Integration Test Report</title>
<style>
    body {{ font-family: monospace; margin: 20px; background: #1e1e1e; color: #d4d4d4; }}
    h1 {{ color: #569cd6; }}
    .summary {{ background: #2d2d2d; padding: 15px; border-radius: 5px; margin: 20px 0; }}
    .pass {{ color: #4ec9b0; }}
    .fail {{ color: #f14c4c; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{ text-align: left; padding: 10px; background: #333; }}
    td {{ padding: 8px 10px; border-bottom: 1px solid #444; }}
    .error {{ color: #f14c4c; }}
    small {{ color: #888; }}
</style>
</head><body>
    <h1>📊 Integration Test Report</h1>
    <div class="summary">
        <b>Test:</b> {self.test_name}<br>
        <b>Started:</b> {self.started_at.strftime('%Y-%m-%d %H:%M:%S')}<br>
        <b>Duration:</b> {self.summary.get('total_duration_sec', 0):.2f} sec<br>
        <b>Result:</b> <span style="color:{status_color}">{'✅ PASS' if self.summary.get('overall_success') else '❌ FAIL'}</span><br>
        <b>Success Rate:</b> {self.summary.get('success_rate', 0):.1f}% ({self.summary.get('steps_passed', 0)}/{self.summary.get('steps_total', 0)} steps)
    </div>
    <table>
        <tr><th>Step</th><th>Duration</th><th>Status</th><th>Details</th></tr>
        {rows}
    </table>
</body></html>
"""

    def save(self, report_dir: str, filename: str):
        """Сохраняет отчёт во всех форматах."""
        Path(report_dir).mkdir(parents=True, exist_ok=True)
        base_path = os.path.join(report_dir, filename)

        with open(f"{base_path}.json", "w", encoding="utf-8") as f:
            f.write(self.to_json())

        with open(f"{base_path}.html", "w", encoding="utf-8") as f:
            f.write(self.to_html())

        # Console output
        print(self.to_console())

        return {
            "json": f"{base_path}.json",
            "html": f"{base_path}.html"
        }