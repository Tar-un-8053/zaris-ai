"""
Test script for the mandatory face verification lock system.
Run: python test_face_lock.py
"""

def main():
    print("=" * 60)
    print("ZARIS AI - Face Verification Lock Test")
    print("=" * 60)
    
    print("\n[1] Testing imports...")
    try:
        from backend.face_rec import get_face_status, face_engine_ready
        print("    face_rec - OK")
    except Exception as e:
        print(f"    face_rec - ERROR: {e}")
        return
    
    print("\n[2] Checking face engine status...")
    is_ready, status_msg = get_face_status()
    print(f"    Ready: {is_ready}")
    print(f"    Status: {status_msg}")
    
    print("\n[3] Testing main.py lock system...")
    from main import is_system_unlocked, set_system_unlocked, _MAX_VERIFICATION_ATTEMPTS
    
    print(f"    System unlocked: {is_system_unlocked()}")
    print(f"    Max verification attempts: {_MAX_VERIFICATION_ATTEMPTS}")
    
    print("\n[4] Simulating lock/unlock...")
    set_system_unlocked(False)
    print(f"    After lock: {is_system_unlocked()}")
    
    set_system_unlocked(True)
    print(f"    After unlock: {is_system_unlocked()}")
    
    print("\n[5] Testing auth status API...")
    try:
        from main import getAuthStatus
        status = getAuthStatus()
        print(f"    unlocked: {status['unlocked']}")
        print(f"    attempts: {status['attempts']}")
        print(f"    max_attempts: {status['max_attempts']}")
    except Exception as e:
        print(f"    Error: {e}")
    
    print("\n" + "=" * 60)
    print("Face lock system test completed!")
    print("=" * 60)
    
    if is_ready:
        print("\n✅ Face engine is READY - System will require face verification on startup")
    else:
        print(f"\n⚠️ Face engine NOT READY: {status_msg}")
        print("   System will require face enrollment first")


if __name__ == "__main__":
    main()
