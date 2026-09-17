from copy import deepcopy
import json

from automatic_timing import estrai_programma_con_titoli


WEEKDAY_TEMPLATE = "infrasettimanale_std"
WEEKEND_TEMPLATE = "fine_settimana_std"


class TemplateService:
    def __init__(self, templates_file, template_state_store):
        self.templates_file = templates_file
        self.template_state_store = template_state_store

    def build_catalog(self):
        templates = self._load_templates()
        dynamic_templates = deepcopy(templates)
        self._apply_dynamic_midweek_program(dynamic_templates)
        self._apply_saved_overrides(dynamic_templates)
        return dynamic_templates

    def save_template_times(self, meeting):
        template_id = meeting.get("id")
        if template_id is None:
            return

        template_state = self.template_state_store.load()
        template_state[str(template_id)] = {
            "conferenceStart": meeting.get("conferenceStart"),
            "conferenceEnd": meeting.get("conferenceEnd"),
        }
        self.template_state_store.save(template_state)

    def _load_templates(self):
        with open(self.templates_file, "r", encoding="utf-8") as file:
            return json.load(file)

    def _apply_dynamic_midweek_program(self, templates):
        midweek_template = self._find_template(templates, WEEKDAY_TEMPLATE)
        if not midweek_template:
            return

        try:
            dynamic_timers = estrai_programma_con_titoli()
        except Exception as error:
            print(f"Fallback attivo. Errore automazione scraper: {error}")
            return

        if dynamic_timers:
            dynamic_timers[0]["start"] = midweek_template["conferenceStart"]
            midweek_template["timers"] = dynamic_timers

    def _apply_saved_overrides(self, templates):
        template_state = self.template_state_store.load()
        for template in templates:
            overrides = template_state.get(str(template.get("id")), {})
            for field in ("conferenceStart", "conferenceEnd"):
                if field in overrides:
                    template[field] = overrides[field]

    @staticmethod
    def _find_template(templates, template_name):
        return next((template for template in templates if template["name"] == template_name), None)
