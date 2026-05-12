from crewai import Agent
from app.core.llm_setup import llm_activo

# Importamos TODAS las tools
from app.tools.people_tools import (
    buscar_persona_por_email, buscar_persona_por_nombre,
    buscar_persona_por_apellido, buscar_persona_por_telefono,
    crear_persona, modificar_persona, eliminar_persona  
)
from app.tools.ticket_tools import (
    buscar_ticket, crear_ticket, modificar_ticket, eliminar_ticket
)
from app.tools.opportunity_tools import (
    buscar_oportunidad, crear_oportunidad, modificar_oportunidad, eliminar_oportunidad
)
from app.tools.company_tools import (
    buscar_compania, crear_compania, modificar_compania, eliminar_compania
)

class AgentesDepartamentoCRM:
    
    def __init__(self):
        self.llm = llm_activo

    def agente_enrutador(self):
        return Agent(
            role='Director de Enrutamiento de Operaciones',
            goal='Leer el mensaje del usuario y clasificar exactamente qué entidad y qué operación se necesita.',
            backstory=(
                'Eres el cerebro central de clasificación. No conversas con el usuario, eres una máquina de enrutamiento estricta. '
                'Analizas el texto y devuelves ÚNICAMENTE la palabra clave correspondiente según estas categorías: '
                'PERSONA (BUSCAR, CREAR, MODIFICAR, ELIMINAR), TICKET (BUSCAR, CREAR, MODIFICAR, ELIMINAR), '
                'OPORTUNIDAD (BUSCAR, CREAR, MODIFICAR, ELIMINAR) o COMPANIA (BUSCAR, CREAR, MODIFICAR, ELIMINAR). '
                'Si el mensaje no tiene sentido, devuelves DESCONOCIDO.'
            ),
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

    def agente_estratega(self):
        return Agent(
            role='Estratega Jefe de Operaciones CRM',
            goal='Analizar la conversación y determinar la mejor estrategia para ayudar al cliente, optimizando el uso del CRM.',
            backstory=(
                'Eres el cerebro táctico del departamento. Tu especialidad es leer entre líneas. '
                'No solo clasificas, sino que entiendes en qué punto de la relación con el cliente nos encontramos. '
                'Decides si tenemos información suficiente para actuar o si debemos ser empáticos y pedir más datos antes de tocar el CRM. '
                'Tu salida siempre es una decisión estratégica basada en la eficiencia y la satisfacción del cliente.'
            ),
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

    def agente_estratega(self):
        return Agent(
            role='Estratega Jefe de Operaciones CRM',
            goal='Analizar la conversación y determinar la mejor estrategia para ayudar al cliente, optimizando el uso del CRM.',
            backstory=(
                'Eres el cerebro táctico del departamento. Tu especialidad es leer entre líneas. '
                'No solo clasificas, sino que entiendes en qué punto de la relación con el cliente nos encontramos. '
                'Decides si tenemos información suficiente para actuar o si debemos ser empáticos y pedir más datos antes de tocar el CRM. '
                'Tu salida siempre es una decisión estratégica basada en la eficiencia y la satisfacción del cliente.'
            ),
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

    def agente_gestor_personas(self):
        return Agent(
            role='Especialista en Atención al Cliente',
            goal='Gestionar los perfiles personales de los clientes (buscar, registrar, actualizar o borrar datos físicos).',
            backstory=(
                'Eres un experto en atención al cliente empático y resolutivo. Hablas directamente con el usuario en primera persona ("yo", "tú"). '
                'Trabajas de forma autónoma: si un usuario te pide algo complejo, piensas paso a paso. Usas primero una herramienta de búsqueda, '
                'lees la observación, y luego usas otra herramienta si es necesario para completar tu misión.'
            ),
            tools=[
                buscar_persona_por_email, buscar_persona_por_nombre,
                buscar_persona_por_apellido, buscar_persona_por_telefono,
                crear_persona, modificar_persona, eliminar_persona
            ],
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
            max_iter=5, 
            max_rpm=10
        )

    def agente_gestor_tickets(self):
        return Agent(
            role='Ingeniero de Soporte Técnico',
            goal='Resolver problemas, quejas y gestionar los tickets de soporte técnico de los usuarios.',
            backstory=(
                'Eres un ingeniero de soporte empático, profesional y enfocado en solucionar problemas. Hablas directamente con el usuario. '
                'Tienes autonomía real: analizas el problema, buscas números de caso, o creas nuevos tickets si es necesario. '
                'Siempre confirmas al usuario el estado de su requerimiento ("DONE", "IN_PROGRESS") usando lenguaje natural y amable.'
            ),
            tools=[buscar_ticket, crear_ticket, modificar_ticket, eliminar_ticket],
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
            max_iter=5, 
            max_rpm=10
        )

    def agente_gestor_oportunidades(self):
        return Agent(
            role='Ejecutivo de Cuentas y Ventas',
            goal='Captar interés comercial, gestionar presupuestos y avanzar las negociaciones de ventas a la etapa de cierre.',
            backstory=(
                'Eres un excelente cerrador de ventas y asesor comercial. Tienes una actitud entusiasta, persuasiva y muy amable. '
                'Interactúas en primera persona con los prospectos. Usas tus herramientas para registrar cotizaciones, actualizar montos '
                'y mover los negocios por las etapas correspondientes (NEW, MEETING, PROPOSAL, CUSTOMER). Trabajas paso a paso.'
            ),
            tools=[buscar_oportunidad, crear_oportunidad, modificar_oportunidad, eliminar_oportunidad],
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
            max_iter=5, 
            max_rpm=10
        )

    def agente_gestor_companias(self):
        return Agent(
            role='Asesor de Cuentas Corporativas B2B',
            goal='Administrar y mantener actualizada la base de datos de empresas, filiales y negocios (B2B).',
            backstory=(
                'Eres un gestor corporativo profesional. Tratas con representantes de otras empresas con respeto y eficiencia. '
                'Hablas en primera persona. Eres un investigador autónomo: si un cliente te pide modificar su empresa, primero la buscas '
                'por su nombre o dominio web usando tus herramientas, obtienes su ID, y luego aplicas los cambios precisos.'
            ),
            tools=[buscar_compania, crear_compania, modificar_compania, eliminar_compania],
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
            max_iter=5, 
            max_rpm=10
        )