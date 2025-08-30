//
//  InternalCode.swift
//  SyntaxAST
//
//  Created by 백승혜 on 8/4/25.
//

import Foundation

class InternalHandler {
    let sourceListPath: String
    let outputDir = "../output/source_json"
    let typealias_outputDir = "../output/typealias_json"
    
    init(sourceListPath: String) {
        self.sourceListPath = sourceListPath
    }

    func readAndProcess() throws {
        let fileList = try String(contentsOfFile: sourceListPath)
        let sourcePaths = fileList.split(separator: "\n").map { String($0) }
        
        var typeResult: [TypealiasInfo] = []
        let lock = NSLock()
        var count: Int = 0
        
        DispatchQueue.concurrentPerform(iterations: sourcePaths.count) { index in let sourcePath = sourcePaths[index]
            do {
                let extractor = try Extractor(sourcePath: sourcePath)
                let typealiasResult = extractor.performExtraction()
                typeResult.append(contentsOf: typealiasResult)
                
                let result = extractor.store.all()
                let encoder = JSONEncoder()
                encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
                let jsonData = try encoder.encode(result)
                
                lock.lock()
                count += 1
                let sourceURL = URL(fileURLWithPath: sourcePath)
                let fileName = sourceURL.deletingPathExtension().lastPathComponent
                let fileNameWithCount = "\(count)_\(fileName)"
                lock.unlock()
                
                var outputURL = URL(fileURLWithPath: outputDir)
                    .appendingPathComponent(fileNameWithCount)
                    .appendingPathExtension("json")
                
                try jsonData.write(to: outputURL)
            } catch {
                print("Error: \(error)")
            }
        }
        if !typeResult.isEmpty {
            let fileName = "typealias"
            var outputURL = URL(fileURLWithPath: typealias_outputDir)
                .appendingPathComponent(fileName)
                .appendingPathExtension("json")
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
            let jsonData = try encoder.encode(typeResult)
            try jsonData.write(to: outputURL)
        }
    }
}
