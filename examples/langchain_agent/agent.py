"""
LangChain Agent Example for flakestorm Testing

This example demonstrates a simple LangChain agent that can be tested with flakestorm.
The agent uses LangChain's Runnable interface to process user queries.

This agent uses Google Gemini AI (if API key is set) or falls back to a mock LLM.
Set GOOGLE_AI_API_KEY or VITE_GOOGLE_AI_API_KEY environment variable to use Gemini.

Compatible with LangChain 0.1.x, 0.2.x, and 0.3.x+
"""

import os
import re
from typing import Any

# Try multiple import strategies for different LangChain versions
chain = None
llm = None


class InputAwareMockLLM:
    """
    A mock LLM that actually processes input, making it suitable for flakestorm testing.
    
    Unlike FakeListLLM, this LLM:
    - Actually reads and processes the input
    - Can fail on certain inputs (empty, too long, injection attempts)
    - Returns responses based on input content
    - Simulates realistic failure modes
    """
    
    def __init__(self):
        self.call_count = 0
    
    def invoke(self, prompt: str, **kwargs: Any) -> str:
        """Process the input and return a response."""
        self.call_count += 1
        
        # Normalize input
        prompt_lower = prompt.lower().strip()
        
        # Failure mode 1: Empty or whitespace-only input
        if not prompt_lower or len(prompt_lower) < 2:
            return "I'm sorry, I didn't understand your question. Could you please rephrase it?"
        
        # Failure mode 2: Very long input (simulates token limit)
        if len(prompt) > 5000:
            return "Your question is too long. Please keep it under 5000 characters."
        
        # Failure mode 3: Detect prompt injection attempts
        injection_patterns = [
            r"ignore\s+(previous|all|above|earlier)",
            r"forget\s+(everything|all|previous)",
            r"system\s*:",
            r"assistant\s*:",
            r"you\s+are\s+now",
            r"new\s+instructions",
        ]
        for pattern in injection_patterns:
            if re.search(pattern, prompt_lower):
                return "I can't follow instructions that ask me to ignore my guidelines. How can I help you with your original question?"
        
        # Generate response based on input content
        # This simulates a real LLM that processes the input
        response_parts = []
        
        # Extract key topics from the input
        if any(word in prompt_lower for word in ["weather", "temperature", "rain", "sunny"]):
            response_parts.append("I can help you with weather information.")
        elif any(word in prompt_lower for word in ["time", "clock", "hour", "minute"]):
            response_parts.append("I can help you with time-related questions.")
        elif any(word in prompt_lower for word in ["capital", "city", "country", "france"]):
            response_parts.append("I can help you with geography questions.")
        elif any(word in prompt_lower for word in ["math", "calculate", "add", "plus", "1 + 1"]):
            response_parts.append("I can help you with math questions.")
        elif any(word in prompt_lower for word in ["email", "write", "professional"]):
            response_parts.append("I can help you write professional emails.")
        elif any(word in prompt_lower for word in ["help", "assist", "support"]):
            response_parts.append("I'm here to help you!")
        else:
            response_parts.append("I understand your question.")
        
        # Add a personalized touch based on input length
        if len(prompt) < 20:
            response_parts.append("That's a concise question!")
        elif len(prompt) > 100:
            response_parts.append("You've provided a lot of context, which is helpful.")
        
        # Add a response based on question type
        if "?" in prompt:
            response_parts.append("Let me provide you with an answer.")
        else:
            response_parts.append("I've noted your request.")
        
        return " ".join(response_parts)
    
    async def ainvoke(self, prompt: str, **kwargs: Any) -> str:
        """Async version of invoke."""
        return self.invoke(prompt, **kwargs)


# Strategy 1: Modern LangChain (0.3.x+) - Use Runnable with Gemini or Mock LLM
try:
    from langchain_core.runnables import RunnableLambda
    
    # Try to use Google Gemini if API key is available
    api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("VITE_GOOGLE_AI_API_KEY")
    
    if api_key:
        try:
            # Try langchain-google-genai (newer package)
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=api_key,
                temperature=0.7,
            )
        except ImportError:
            try:
                # Try langchain-community (older package)
                from langchain_community.chat_models import ChatGoogleGenerativeAI
                llm = ChatGoogleGenerativeAI(
                    model="gemini-2.5-flash",
                    google_api_key=api_key,
                    temperature=0.7,
                )
            except ImportError:
                # Fallback to mock LLM if packages not installed
                print("Warning: langchain-google-genai not installed. Using mock LLM.")
                print("Install with: pip install langchain-google-genai")
                llm = InputAwareMockLLM()
    else:
        # No API key, use mock LLM
        print("Warning: GOOGLE_AI_API_KEY not set. Using mock LLM.")
        print("Set GOOGLE_AI_API_KEY environment variable to use Google Gemini.")
        llm = InputAwareMockLLM()
    
    def process_input(input_dict):
        """Process input and return response."""
        user_input = input_dict.get("input", str(input_dict))
        
        # Handle both ChatModel (returns AIMessage) and regular LLM (returns str)
        if hasattr(llm, "invoke"):
            response = llm.invoke(user_input)
            # Extract text from AIMessage if needed
            if hasattr(response, "content"):
                response_text = response.content
            elif isinstance(response, str):
                response_text = response
            else:
                response_text = str(response)
        else:
            # Fallback for mock LLM
            response_text = llm.invoke(user_input)
        
        # Return dict format that flakestorm expects
        return {"output": response_text, "text": response_text}
    
    chain = RunnableLambda(process_input)
    
except ImportError:
    # Strategy 2: LangChain 0.2.x - Use LLMChain with Gemini or Mock LLM
    try:
        from langchain.chains import LLMChain
        from langchain.prompts import PromptTemplate
        
        prompt_template = PromptTemplate(
            input_variables=["input"],
            template="""You are a helpful assistant. Answer the user's question clearly and concisely.

User question: {input}

Assistant response:""",
        )
        
        # Try to use Google Gemini if API key is available
        api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("VITE_GOOGLE_AI_API_KEY")
        
        if api_key:
            try:
                from langchain_community.chat_models import ChatGoogleGenerativeAI
                llm = ChatGoogleGenerativeAI(
                    model="gemini-2.5-flash",
                    google_api_key=api_key,
                    temperature=0.7,
                )
            except ImportError:
                print("Warning: langchain-google-genai not installed. Using mock LLM.")
                llm = InputAwareMockLLM()
        else:
            print("Warning: GOOGLE_AI_API_KEY not set. Using mock LLM.")
            llm = InputAwareMockLLM()
        
        # Create a wrapper that makes the LLM compatible with LLMChain
        # LLMChain will call the LLM with the formatted prompt, so we extract the user input
        class LLMWrapper:
            def __call__(self, prompt: str, **kwargs: Any) -> str:
                # Extract user input from the formatted prompt template
                if "User question:" in prompt:
                    parts = prompt.split("User question:")
                    if len(parts) > 1:
                        user_input = parts[-1].split("Assistant response:")[0].strip()
                    else:
                        user_input = prompt
                else:
                    user_input = prompt
                
                # Handle ChatModel (returns AIMessage) vs regular LLM (returns str)
                if hasattr(llm, "invoke"):
                    response = llm.invoke(user_input)
                    if hasattr(response, "content"):
                        return response.content
                    elif isinstance(response, str):
                        return response
                    else:
                        return str(response)
                else:
                    return llm.invoke(user_input)
        
        chain = LLMChain(llm=LLMWrapper(), prompt=prompt_template)
        
    except ImportError:
        # Strategy 3: LangChain 0.1.x or alternative structure
        try:
            from langchain import LLMChain, PromptTemplate
            
            prompt_template = PromptTemplate(
                input_variables=["input"],
                template="""You are a helpful assistant. Answer the user's question clearly and concisely.

User question: {input}

Assistant response:""",
            )
            
            # Try to use Google Gemini if API key is available
            api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("VITE_GOOGLE_AI_API_KEY")
            
            if api_key:
                try:
                    from langchain_community.chat_models import ChatGoogleGenerativeAI
                    llm = ChatGoogleGenerativeAI(
                        model="gemini-2.5-flash",
                        google_api_key=api_key,
                        temperature=0.7,
                    )
                except ImportError:
                    print("Warning: langchain-google-genai not installed. Using mock LLM.")
                    llm = InputAwareMockLLM()
            else:
                print("Warning: GOOGLE_AI_API_KEY not set. Using mock LLM.")
                llm = InputAwareMockLLM()
            
            class LLMWrapper:
                def __call__(self, prompt: str, **kwargs: Any) -> str:
                    # Extract user input from the formatted prompt template
                    if "User question:" in prompt:
                        parts = prompt.split("User question:")
                        if len(parts) > 1:
                            user_input = parts[-1].split("Assistant response:")[0].strip()
                        else:
                            user_input = prompt
                    else:
                        user_input = prompt
                    
                    # Handle ChatModel (returns AIMessage) vs regular LLM (returns str)
                    if hasattr(llm, "invoke"):
                        response = llm.invoke(user_input)
                        if hasattr(response, "content"):
                            return response.content
                        elif isinstance(response, str):
                            return response
                        else:
                            return str(response)
                    else:
                        return llm.invoke(user_input)
            
            chain = LLMChain(llm=LLMWrapper(), prompt=prompt_template)
            
        except ImportError:
            # Strategy 4: Simple callable wrapper (works with any version)
            class SimpleChain:
                """Simple chain wrapper that works with any LangChain version."""
                
                def __init__(self):
                    self.mock_llm = InputAwareMockLLM()
                
                def invoke(self, input_dict):
                    """Invoke the chain synchronously."""
                    user_input = input_dict.get("input", str(input_dict))
                    response = self.mock_llm.invoke(user_input)
                    return {"output": response, "text": response}
                
                async def ainvoke(self, input_dict):
                    """Invoke the chain asynchronously."""
                    return self.invoke(input_dict)
            
            chain = SimpleChain()

if chain is None:
    raise ImportError(
        "Could not import LangChain. Install with: pip install langchain langchain-core langchain-community"
    )

# Export the chain for flakestorm to use
# flakestorm will call: chain.invoke({"input": prompt}) or chain.ainvoke({"input": prompt})
# The adapter handles different LangChain interfaces automatically
__all__ = ["chain"]

