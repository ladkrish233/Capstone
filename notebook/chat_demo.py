from notebook.tools_demo import agent

message_history = []

while True:
    user_input = input("You : ")
    if user_input == "q":
        break
    result = agent.run_sync(user_input, message_history=message_history)
    message_history += result.new_messages()
    print(result.output)
    print(result.usage)
