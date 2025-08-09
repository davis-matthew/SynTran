#include "llvm/ExecutionEngine/Orc/LLJIT.h"
#include "llvm/ExecutionEngine/Orc/ThreadSafeModule.h"
#include "llvm/IR/Module.h"
#include "llvm/Pass.h"

using namespace llvm;
using namespace llvm::orc;

namespace {
struct RunFunctionPass : public FunctionPass {
  static char ID;
  RunFunctionPass() : ModulePass(ID) {}

  llvm::SmallVector<long long, 20> runOnModule(Function &F) override {
    Module M = *F.getParent();

    // Create LLJIT instance
    auto JIT = cantFail(LLJITBuilder().create());

    // Wrap the module in a ThreadSafeModule
    auto TSM = ThreadSafeModule(std::make_unique<Module>(M), std::make_unique<LLVMContext>());

    // Add module to JIT
    cantFail(JIT->addIRModule(std::move(TSM)));

    // Lookup the function
    auto Sym = JIT->lookup("foo");
    if (!Sym) {
      errs() << "Function 'foo' not found\n";
      return false;
    }

    // Cast to function pointer
    using FuncType = int(*)(int);
    auto *FooFunc = (FuncType)Sym->getAddress();

    llvm::SmallVector<long long, 20> results;
    for (int i = 0; i < 20; ++i) {
      results.push_back(FooFunc(i));
    }


    return results;
  }
};

char RunFunctionPass::ID = 0;
static RegisterPass<RunFunctionPass> X("run-func", "Run Function with ORCv2");
} // namespace