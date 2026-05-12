from app.crews.department import DepartamentoCRMCrew

def iniciar_chat_interactivo():
    print("="*60)
    print(" 🚀 INICIANDO MODO CHAT - AGENTIC CRM CON MEMORIA")
    print("    (Escribe 'salir', 'exit' o 'quit' para terminar)")
    print("="*60)

    # 1. Instanciamos el departamento UNA SOLA VEZ. 
    # Esto mantiene viva la lista 'historial_chat' durante toda la sesión.
    departamento = DepartamentoCRMCrew()
    # 2. Iniciamos el bucle infinito del chat
    while True:
        # Obtenemos el input del usuario en la consola
        mensaje_usuario = input("\n🧑 Cliente: ")
        
        # Condición para salir del bucle y cerrar el programa
        if mensaje_usuario.lower().strip() in ['salir', 'exit', 'quit']:
            print("\n[👋] Apagando el sistema Agentic CRM. ¡Hasta luego!")
            break

        print("\n🤖 Procesando solicitud (Por favor espera)...\n")
        
        # 3. Enviamos el mensaje al orquestador
        respuesta = departamento.procesar_solicitud(mensaje_usuario)
        
        # 4. Imprimimos la respuesta final en la consola
        print("\n========================================")
        print("          RESPUESTA DEL ASISTENTE       ")
        print("========================================")
        print(f"👩‍💼 Recepcionista: {respuesta}\n")

if __name__ == "__main__":
    iniciar_chat_interactivo()